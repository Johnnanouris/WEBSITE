import sys
import time
import re
import threading
import traceback
import io
import ujson as json


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


# Global lists to store products from different sources
skroutz_products = []
insomnia_products = []
vendora_products = []
products_lock = threading.Lock()

def is_valid_product_link(link):
    """Validate if the link is a valid product link."""
    if not link:
        return False
    
    excluded_patterns = [
        "/user/items/boosts",
        "/items/create",
        "/user/items/",
        "/search",
        "/account",
        "/login",
        "/register",
        "/category/",
        "/cart",
        "/checkout"
    ]
    
    for pattern in excluded_patterns:
        if pattern in link:
            return False
    
    return (
        "/items/" in link and 
        not link.endswith("/items/") and 
        not link.endswith("/items") and
        len(link.split("/")[-1]) > 2  # Αποκλείει πολύ σύντομα URLs
    )

def extract_price(text):
    """Εκτεταμένη εξαγωγή τιμών με πολλαπλές τεχνικές."""
    if not text:
        return None
    
    price_patterns = [
        r'(\d+[.,]?\d*)\s*€',    # 100 €
        r'€\s*(\d+[.,]?\d*)',    # € 100
        r'(\d+[.,]?\d*)\s*ευρώ', # 100 ευρώ
        r'^(\d+[.,]?\d*)$'       # Μόνο αριθμός
    ]
    
    for pattern in price_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                price = float(match.group(1).replace(',', '.'))
                return price
            except (ValueError, TypeError):
                continue
    
    return None


def search_skroutz(search_term, min_price, max_price):
    global skroutz_products
    skroutz_products = []  # Reset for each search
    
    options = webdriver.FirefoxOptions()
    options.add_argument('--headless')
    options.add_argument('--window-size=1920,1080')
    driver = webdriver.Firefox(options=options)
    
    # Ορισμός timeout φόρτωσης σελίδας
    driver.set_page_load_timeout(2)
    
    # Δημιουργία αντικειμένων αναμονής με διαφορετικά timeouts
    short_wait = WebDriverWait(driver, 0.1)   # Σύντομη αναμονή
    wait = WebDriverWait(driver, 0.1)        # Κανονική αναμονή
    
    try:
        url = f"https://www.skroutz.gr/skoop?keyphrase={search_term.replace(' ', '+')}"        
        # Φόρτωση της σελίδας
        driver.get(url)
        
        # Περίμενε για ένα βασικό στοιχείο που δείχνει ότι η σελίδα φόρτωσε
        try:
            # Περίμενε για οποιοδήποτε από αυτά τα στοιχεία - όποιο φορτώσει πρώτο
            page_loaded = wait.until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".sku-card, .c2c-item-card, .card, article")),
                    EC.presence_of_element_located((By.TAG_NAME, "footer")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='product']"))
                )
            )
        except:
            print("Basic page load detection timed out, continuing anyway")
        
        # Σταμάτησε επιπλέον αιτήματα δικτύου μετά τη φόρτωση βασικών στοιχείων
        driver.execute_script("""
            window.stop();
            // Απενεργοποίηση άλλων αιτημάτων που δεν είναι σημαντικά
            const originalFetch = window.fetch;
            window.fetch = function() {
                const url = arguments[0];
                if (url.includes('analytics') || url.includes('tracking') || url.includes('ads')) {
                    console.log('Blocked fetch:', url);
                    return new Promise(() => {});
                }
                return originalFetch.apply(this, arguments);
            }
        """)
        
        # Χειρισμός cookie banner - με σύντομο timeout
        try:
            cookie_selectors = [
                "//button[contains(text(), 'Αποδοχή')]",
                "//button[contains(@class, 'accept')]",
                "//*[contains(@class, 'cookie-accept')]",
                "//button[text()='Αποδοχή όλων']"
            ]
            
            for selector in cookie_selectors:
                try:
                    cookie_button = short_wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    cookie_button.click()
                    print("Cookie accepted", file=sys.stderr)
                    break
                except:
                    continue
        except:
            print("No cookie banner or couldn't accept", file=sys.stderr)
        
        # Γρήγορο scroll για φόρτωση δυναμικού περιεχομένου
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.3);")
        time.sleep(0.025)  # Μικρότερος χρόνος αναμονής
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.6);")
        time.sleep(0.025)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.025)
        
        # Βελτιωμένοι επιλογείς προϊόντων για Skroutz Skoop
        product_selectors = [
            "//li[contains(@class, 'sku-card')]",  # Βασικός επιλογέας από την ανάλυση
            "//li[contains(@class, 'c2c-item-card')]",  # Άλλος συνηθισμένος
            "//div[contains(@class, 'card')]",
            "//div[contains(@class, 'product-card')]",
            "//article[contains(@class, 'card')]",
            "//article[contains(@class, 'skoop-item')]"
        ]
        
        products = []
        for selector in product_selectors:
            try:
                found_products = driver.find_elements(By.XPATH, selector)
                if found_products:
                    products = found_products
                    break
            except Exception as e:
                continue
        
        # Εναλλακτική μέθοδος με JavaScript αν οι επιλογείς δεν βρήκαν προϊόντα
        if not products or len(products) < 2:
            # Εναλλακτική προσέγγιση με JavaScript για εξαγωγή προϊόντων
            products_data = driver.execute_script("""
                return Array.from(document.querySelectorAll('li.sku-card, li.c2c-item-card, div.card, article.card')).map(card => {
                    try {
                        // Τίτλος
                        let title = '';
                        const titleEl = card.querySelector('h2, h3, a.js-sku-link, .sku-name, .product-name');
                        if (titleEl) title = titleEl.textContent.trim();
                        
                        // Σύνδεσμος
                        let link = '';
                        const linkEl = card.querySelector('a.js-sku-link, a[href*="/skoop/items/"]');
                        if (linkEl) link = linkEl.href;
                        
                        // Τιμή
                        let price = '';
                        const priceEl = card.querySelector('.price, [class*="price"], [class*="amount"]');
                        if (priceEl) price = priceEl.textContent.trim();
                        
                        // Εικόνα
                        let image = null;
                        // Προσπάθεια να βρούμε εικόνα μέσα στην κάρτα
                        const imgContainer = card.querySelector('.image-container, .sku-card-pic, [class*="image"]');
                        const img = imgContainer ? imgContainer.querySelector('img') : card.querySelector('img');
                        
                        if (img) {
                            image = img.src || img.getAttribute('data-src');
                        }
                        
                        return { title, link, price, image };
                    } catch(e) {
                        return null;
                    }
                }).filter(item => item && item.title && item.link);
            """)
            
            
            # Μετατροπή των JavaScript αποτελεσμάτων σε προϊόντα
            if products_data and len(products_data) > 0:
                for product_data in products_data:
                    try:
                        title = product_data.get('title', '').strip()
                        price_text = product_data.get('price', '').strip()
                        link = product_data.get('link', '')
                        image_url = product_data.get('image')
                        
                        if not title or not link or not is_valid_product_link(link):
                            continue
                        
                        # Debug log
                        
                        # Εξαγωγή τιμής
                        price = extract_price(price_text)
                        if price is not None and min_price <= price <= max_price:
                            # Έλεγχος αν είναι διπλότυπο
                            is_duplicate = any(link == existing[2] for existing in skroutz_products)
                            if not is_duplicate:
                                with products_lock:
                                    skroutz_products.append((title, price, link, image_url))
                    except Exception as e:
                        continue
            
            # Δοκιμή απευθείας εξαγωγής εικόνων με βάση την ανάλυση JSON
            if not skroutz_products or len(skroutz_products) < 3:
                # Εξαγωγή όλων των εικόνων
                all_images = driver.execute_script("""
                    return Array.from(document.querySelectorAll('img')).map(img => {
                        const rect = img.getBoundingClientRect();
                        const parent = img.closest('li.sku-card, li.c2c-item-card, div.card, article.card');
                        
                        return {
                            src: img.src,
                            dataSrc: img.getAttribute('data-src'),
                            width: img.width,
                            height: img.height,
                            alt: img.alt,
                            inViewport: (
                                rect.top >= 0 &&
                                rect.left >= 0 &&
                                rect.bottom <= window.innerHeight &&
                                rect.right <= window.innerWidth
                            ),
                            hasParentCard: parent !== null,
                            parentId: parent ? parent.id : null
                        };
                    }).filter(img => (img.src && img.src.includes('scdn.gr') && img.width > 50 && img.height > 50));
                """)
                
                
                # Προσπάθεια να συνδέσουμε τις εικόνες με προϊόντα
                if all_images and len(all_images) > 0:
                    # Εξαγωγή μόνο των συνδέσμων προϊόντων
                    product_links = driver.execute_script("""
                        return Array.from(document.querySelectorAll('a.js-sku-link, a[href*="/skoop/items/"]')).map(a => {
                            return {
                                href: a.href,
                                title: a.textContent.trim() || a.getAttribute('title'),
                                parentCard: a.closest('li.sku-card, li.c2c-item-card, div.card, article.card'),
                                parentId: a.closest('li.sku-card, li.c2c-item-card, div.card, article.card') ? 
                                          a.closest('li.sku-card, li.c2c-item-card, div.card, article.card').id : null,
                                nearestPriceText: (() => {
                                    // Προσπάθεια να βρούμε την τιμή κοντά στον σύνδεσμο
                                    const priceEl = a.parentElement.querySelector('[class*="price"], [class*="amount"]') ||
                                                  a.closest('li, div, article').querySelector('[class*="price"], [class*="amount"]');
                                    return priceEl ? priceEl.textContent.trim() : '';
                                })()
                            };
                        }).filter(link => link.href && link.href.includes('/skoop/items/') && link.title);
                    """)
                    
                    
                    # Για κάθε σύνδεσμο προϊόντος, προσπάθησε να βρεις μια αντίστοιχη εικόνα
                    for product_link in product_links:
                        try:
                            link = product_link.get('href', '')
                            title = product_link.get('title', '')
                            price_text = product_link.get('nearestPriceText', '')
                            parent_id = product_link.get('parentId')
                            
                            if not is_valid_product_link(link):
                                continue
                                
                            # Εκχώρηση εικόνας με βάση το parent ID ή εγγύτητα
                            image_url = None
                            
                            # Αν έχουμε parent ID, κάνε αντιστοίχιση
                            if parent_id:
                                for img in all_images:
                                    if img.get('parentId') == parent_id:
                                        image_url = img.get('src') or img.get('dataSrc')
                                        break
                            
                            # Αν δεν βρέθηκε εικόνα, πάρε μια από τις εικόνες που πρέπει να είναι προϊόντα
                            if not image_url and all_images:
                                # Δοκιμή με βάση το ID προϊόντος
                                item_id_match = re.search(r'/items/(\d+)', link)
                                if item_id_match:
                                    item_id = item_id_match.group(1)
                                    for img in all_images:
                                        img_src = img.get('src', '')
                                        if item_id in img_src:
                                            image_url = img_src
                                            break
                            
                            # Τελευταία προσπάθεια: πάρε οποιαδήποτε εικόνα προϊόντος που δεν έχει χρησιμοποιηθεί
                            if not image_url and all_images:
                                # Έλεγχος αν η εικόνα έχει ήδη χρησιμοποιηθεί
                                used_images = [item[3] for item in skroutz_products if item[3]]
                                for img in all_images:
                                    img_src = img.get('src', '')
                                    if img_src not in used_images and 'thumbnail' in img_src:
                                        image_url = img_src
                                        break
                            
                            price = extract_price(price_text)
                            if price is not None and min_price <= price <= max_price:
                                is_duplicate = any(link == existing[2] for existing in skroutz_products)
                                if not is_duplicate:
                                    with products_lock:
                                        skroutz_products.append((title, price, link, image_url))
                        except Exception as e:
                            print("Error processing product link")
        
        # Αν έχουμε product cards, επεξεργασία με την κανονική ροή
        else:
            for product in products:
                try:
                    # Βελτιωμένη εξαγωγή τίτλου
                    title_selectors = [
                        ".//h2",
                        ".//h3",
                        ".//*[contains(@class, 'title')]",
                        ".//*[contains(@class, 'name')]",
                        ".//a[contains(@class, 'js-sku-link')]",
                        ".//a[contains(@href, '/skoop/items/')]"
                    ]
                    
                    title = None
                    for title_selector in title_selectors:
                        try:
                            title_element = product.find_element(By.XPATH, title_selector)
                            title = title_element.text.strip()
                            if title:
                                break
                        except:
                            continue
                    
                    if not title:
                        # Fallback: try getting text from the entire product card
                        title = product.text.split('\n')[0].strip()
                    
                    # Βελτιωμένη εξαγωγή τιμής
                    price_selectors = [
                        ".//span[contains(text(),'€')]",
                        ".//*[contains(@class, 'price')]",
                        ".//*[contains(text(),'€')]",
                        ".//*[contains(@class, 'amount')]"
                    ]
                    
                    price_text = None
                    for price_selector in price_selectors:
                        try:
                            price_element = product.find_element(By.XPATH, price_selector)
                            price_text = price_element.text.strip()
                            if price_text:
                                break
                        except:
                            continue
                    
                    # Εξαγωγή συνδέσμου
                    link_selectors = [
                        ".//a[contains(@class, 'js-sku-link')]",
                        ".//a[contains(@href, '/skoop/items/')]",
                        ".//a[contains(@href, '/products/')]",
                        ".//a"
                    ]
                    
                    link = None
                    for link_selector in link_selectors:
                        try:
                            link_element = product.find_element(By.XPATH, link_selector)
                            link = link_element.get_attribute("href")
                            if link and is_valid_product_link(link):
                                break
                        except:
                            continue
                    
                    # Βελτιωμένη εξαγωγή εικόνας με βάση το JSON ανάλυσης
                    image_url = None
                    image_selectors = [
                        ".//div[contains(@class, 'image-container')]//img",  # Βασικός επιλογέας από την ανάλυση
                        ".//div[contains(@class, 'sku-card-pic')]//img",     # Βασικός επιλογέας από την ανάλυση
                        ".//img",                                            # Όποια εικόνα υπάρχει
                        ".//*[contains(@class, 'image')]//img"
                    ]

                    for image_selector in image_selectors:
                        try:
                            image_elements = product.find_elements(By.XPATH, image_selector)
                            for image_element in image_elements:
                                # Έλεγχος για συγκεκριμένα μοτίβα εικόνων Skroutz
                                src = image_element.get_attribute("src")
                                if src and ('scdn.gr' in src or 'skroutz.gr' in src) and not src.endswith('.png'):
                                    # Φιλτράρισμα των favicon και άλλων μικρών εικόνων
                                    width = image_element.get_attribute("width")
                                    height = image_element.get_attribute("height")
                                    try:
                                        if width and height and int(width) > 50 and int(height) > 50:
                                            image_url = src
                                            break
                                    except:
                                        # Αν δεν μπορούμε να μετατρέψουμε τις διαστάσεις, δεχόμαστε την εικόνα αν περιέχει 'thumbnail'
                                        if 'thumbnail' in src:
                                            image_url = src
                                            break
                                # Έλεγχος για data-src
                                data_src = image_element.get_attribute("data-src")
                                if not image_url and data_src and ('scdn.gr' in data_src or 'skroutz.gr' in data_src):
                                    image_url = data_src
                                    break
                            if image_url:
                                break
                        except Exception as e:
                            continue
                    
                    # Αν δεν βρέθηκε εικόνα, δοκιμή να κατασκευαστεί το URL εικόνας από το ID του προϊόντος
                    if not image_url and link:
                        try:
                            item_id_match = re.search(r'/items/(\d+)', link)
                            if item_id_match:
                                item_id = item_id_match.group(1)
                                # Το μοτίβο των εικόνων Skroutz από το JSON ανάλυσης
                                domain = 'a.scdn.gr' if int(item_id) % 3 == 0 else ('b.scdn.gr' if int(item_id) % 3 == 1 else 'c.scdn.gr')
                                image_url = f"https://{domain}/ds/c2c/item_images/h-{item_id}/thumbnail_recent.jpeg"
                        except Exception as e:
                            print(" URL construction error")
                    
                    # Εξαγωγή τιμής και προσθήκη στα αποτελέσματα
                    price = extract_price(price_text or '')
                    
                    if price is not None and title and link:
                        if min_price <= price <= max_price:
                            with products_lock:
                                skroutz_products.append((title, price, link, image_url))
                
                except Exception as e:
                    print("Skroutz product error")
    
    except Exception as e:
        print("Skroutz search error")
    
    finally:
        driver.quit()

def search_insomnia(search_term, min_price, max_price, max_pages=5):
    """
    Αναζήτηση στο Insomnia.gr με βάση τον όρο αναζήτησης και εύρος τιμής.
    Εξάγει όλες τις πληροφορίες χωρίς να ανοίγει κάθε αγγελία ξεχωριστά.
    """
    global insomnia_products
    insomnia_products = []  # Reset για κάθε αναζήτηση
    
    # Ρυθμίσεις Firefox
    options = webdriver.FirefoxOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-extensions')
    options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    options.page_load_strategy = 'eager'  # Φόρτωση μόνο του βασικού περιεχομένου
    
    # Εκκίνηση WebDriver
    driver = webdriver.Firefox(options=options)
    driver.set_page_load_timeout(1.5)
    wait = WebDriverWait(driver, 1.5)
    
    try:
        # Δημιουργία URL αναζήτησης
        base_url = f"https://www.insomnia.gr/search/?q={search_term.replace(' ', '%20')}&quick=1&page="
        
        for page in range(1, max_pages + 1):
            
            # Φόρτωση σελίδας αποτελεσμάτων
            try:
                url = base_url + str(page)
                driver.get(url)
                time.sleep(1)  # Σύντομη αναμονή για φόρτωση
            except Exception as e:
                continue
            
            # Προσθήκη κώδικα για σταδιακό scroll με καλύτερο τρόπο
            # για να βεβαιωθούμε ότι όλα τα στοιχεία φορτώνονται σωστά
            try:
                last_height = driver.execute_script("return document.body.scrollHeight")
                scroll_pause_time = 0.5
                scroll_attempts = 2
                max_scroll_attempts = 5  # Μέγιστος αριθμός προσπαθειών scroll
                
                while scroll_attempts < max_scroll_attempts:
                    # Scroll προς τα κάτω
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(scroll_pause_time)
                    
                    # Υπολογισμός νέου ύψους scroll
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    
                    # Αν δεν αλλάξει το ύψος, έχουμε φτάσει στο τέλος
                    if new_height == last_height:
                        break
                    
                    last_height = new_height
                    scroll_attempts += 1
                
                # Επιστροφή στην κορυφή για να ξεκινήσουμε την εξαγωγή δεδομένων
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(scroll_pause_time)
            except Exception as e:
                print("Σφάλμα κατά το scroll")
                
            # Έλεγχος αν η σελίδα έχει φορτωθεί σωστά
            if "insomnia" not in driver.title.lower():
                continue
            
            # Εύρεση όλων των αγγελιών στην τρέχουσα σελίδα
            try:
                listings = driver.find_elements(By.CSS_SELECTOR, "li.ipsStreamItem")
                
                for listing in listings:
                    try:
                        # Έλεγχος αν είναι διαφήμιση/προωθητική αγγελία
                        ad_elements = listing.find_elements(By.XPATH, "./ancestor::div[contains(@class, 'ipsAdvertisement') or contains(@class, 'ipsSponsor') or contains(@class, 'ipsAd')]")
                        if ad_elements:
                            continue
                        
                        # Εξαγωγή τίτλου
                        title_element = listing.find_elements(By.CSS_SELECTOR, "h2.ipsStreamItem_title a")
                        if not title_element:
                            continue
                            
                        title = title_element[0].text.strip()
                        
                        # Φιλτράρισμα με βάση τον όρο αναζήτησης στον τίτλο
                        if search_term.lower() not in title.lower():
                            continue
                        
                        # Εξαγωγή τιμής
                        try:
                            price_element = listing.find_elements(By.CLASS_NAME, "ipsStream_price")
                            if not price_element:
                                continue
                                
                            price_text = price_element[0].text.strip()
                            price = extract_price(price_text)
                            
                            if price is None:
                                # Εναλλακτική μέθοδος εξαγωγής τιμής
                                import re
                                price_match = re.search(r"(\d+[.,]?\d*)", price_text)
                                if not price_match:
                                    continue
                                price = float(price_match.group(1).replace(',', '.'))
                        except Exception as e:
                            continue
                        
                        # Έλεγχος τιμής στο εύρος που ζητήθηκε
                        if not (min_price <= price <= max_price):
                            continue
                        
                        # Εξαγωγή συνδέσμου
                        link = title_element[0].get_attribute("href")
                        
                        # Εξαγωγή εικόνας απευθείας από το item της λίστας αναζήτησης
                        image_url = None
                        try:
                            # Πρώτη προσπάθεια - αναζήτηση εικόνας μέσα στο στοιχείο λίστας
                            img_elements = listing.find_elements(By.CSS_SELECTOR, "img.ipsImage")
                            if not img_elements:
                                img_elements = listing.find_elements(By.CSS_SELECTOR, "img.ipsStreamItem_image")
                            if not img_elements:
                                img_elements = listing.find_elements(By.TAG_NAME, "img")
                                
                            if img_elements:
                                # Προτιμάμε data-src αν υπάρχει (lazy loading)
                                src = img_elements[0].get_attribute("data-src")
                                if not src:
                                    src = img_elements[0].get_attribute("src")
                                    
                                if src:
                                    if src.startswith("//"):
                                        src = "https:" + src
                                    image_url = src
                        except Exception as e:
                            print("Σφάλμα εξαγωγής εικόνας")
                        
                        # Προσθήκη προϊόντος στη λίστα αν δεν υπάρχει ήδη
                        if not any(link == existing[2] for existing in insomnia_products):
                            with products_lock:
                                insomnia_products.append((title, price, link, image_url))
                    
                    except Exception as e:
                        continue
            
            except Exception as e:
                continue
    
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
    
    finally:
        try:
            driver.quit()
        except:
            pass
    
    return insomnia_products

def extract_price(price_text):
    """Βοηθητική συνάρτηση για την εξαγωγή τιμής από το κείμενο"""
    import re
    
    # Αφαίρεση μη αριθμητικών χαρακτήρων εκτός από τον αριθμό και τα σύμβολα . και ,
    price_text = price_text.replace("€", "").strip()
    price_match = re.search(r"(\d+[.,]?\d*)", price_text)
    
    if price_match:
        try:
            price_str = price_match.group(1).replace(',', '.')
            return float(price_str)
        except:
            pass
    
    return None

def safe_print(message, file=sys.stderr):
    """
    Safely print messages with Unicode characters by handling encoding errors.
    
    Args:
        message (str): The message to print
        file (file object): The file to write to (default is sys.stderr)
    """
    try:
        # Try to write with the current encoding
        print(message, file=file)
    except UnicodeEncodeError:
        # If encoding fails, try different approaches
        try:
            # Attempt to force UTF-8 encoding
            print(message.encode('utf-8', errors='replace').decode('utf-8'), file=file)
        except Exception:
            # Absolute fallback: remove non-ASCII characters
            safe_message = ''.join(char for char in message if ord(char) < 128)
            print(safe_message, file=file)

def search_vendora(search_term, min_price, max_price):
    global vendora_products
    vendora_products = []  # Reset for each search
    
    # Redirect stderr to handle encoding issues
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    options = webdriver.FirefoxOptions()
    options.add_argument('--headless')  # Enable headless mode
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')  # Larger window for headless mode
    options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.9999.99 Safari/537.36")
    
    # Βελτιστοποίηση φόρτωσης σελίδας
    options.set_preference("network.cookie.cookieBehavior", 0)  # Accept all cookies
    options.set_preference("network.cookie.lifetimePolicy", 0)  # Keep cookies until expiration
    options.set_preference("privacy.cookies.cookieBehavior", 0)  # Accept all cookies
    options.set_preference("dom.disable_beforeunload", True)  # Disable pre-exit warnings
    options.set_preference("browser.tabs.disableBackgroundZombification", False)  # Speed up tab switching
    options.set_preference("network.http.pipelining", True)  # Enable HTTP pipelining
    options.set_preference("network.http.proxy.pipelining", True)
    options.set_preference("network.http.max-connections", 256)  # Increase max connections
    options.set_preference("network.http.max-connections-per-server", 32)

    driver = webdriver.Firefox(options=options)
    wait = WebDriverWait(driver, 2)  # Μειωμένος χρόνος αναμονής για πιο επιθετική αναζήτηση

    try:
        # Direct search URL
        direct_url = f"https://vendora.gr/items?q={search_term.replace(' ', '+')}"
        driver.get(direct_url)
        safe_print(f"Navigating to URL: {direct_url}")
        time.sleep(3)  # Μειωμένος χρόνος αναμονής αρχικής φόρτωσης

        # Scroll to load more results
        safe_print("Loading more results...")
        previous_product_count = 0
        max_attempts = 4  # Μειώσαμε τον αριθμό των προσπαθειών για ταχύτερη εκτέλεση
        attempts = 0
        no_new_products_count = 0

        while attempts < max_attempts:
            # Μετρήστε τον τρέχοντα αριθμό προϊόντων
            current_count = len(driver.find_elements(By.CSS_SELECTOR, 'a[href*="/items/"]'))
            safe_print(f"Current product count: {current_count}")
            
            # Εάν δεν προστέθηκαν νέα προϊόντα, αυξήστε τον μετρητή
            if current_count == previous_product_count:
                no_new_products_count += 1
                if no_new_products_count >= 2:  # Τερματισμός μετά από 2 συνεχόμενες προσπάθειες χωρίς νέα προϊόντα
                    safe_print("No new products after multiple scrolls. Finished loading.")
                    break
            else:
                no_new_products_count = 0  # Επαναφορά μετρητή αν βρέθηκαν νέα προϊόντα
            
            # Αποθηκεύστε τον τρέχοντα αριθμό προϊόντων για σύγκριση
            previous_product_count = current_count
            
            # Πιο επιθετικό scrolling για ταχύτερη φόρτωση
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.2);")
            time.sleep(0.5)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.4);")
            time.sleep(0.5)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.6);")
            time.sleep(0.5)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.8);")
            time.sleep(0.5)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.1)
            
            attempts += 1

        safe_print(f"Finished loading after {attempts} scroll attempts. Found {previous_product_count} potential product links.")
                
        # JavaScript to extract products with images - βελτιστοποιημένο για ταχύτητα
        js_products = driver.execute_script("""
        const products = [];
        const productLinks = Array.from(document.querySelectorAll('a[href*="/items/"]'));
        const processedUrls = new Set();
        
        for (const link of productLinks) {
            if (!link.href || 
                link.href.includes('/user/items/') || 
                link.href.includes('/items/create') ||
                processedUrls.has(link.href)) continue;
            
            processedUrls.add(link.href);
            
            let title = link.textContent.trim() || link.querySelector('h2, h3, h4')?.textContent.trim() || link.href.split('/').pop().replace(/-/g, ' ');
            
            let priceText = '';
            const priceRegex = /(\\d+[.,]?\\d*)\\s*€|€\\s*(\\d+[.,]?\\d*)|\\b(\\d+[.,]?\\d*)\\s*ευρώ\\b/i;
            
            // Optimized price search - look directly at link first, then one parent up
            const match = link.textContent.match(priceRegex);
            if (match) {
                priceText = match[0];
            } else if (link.parentElement) {
                const parentMatch = link.parentElement.textContent.match(priceRegex);
                if (parentMatch) priceText = parentMatch[0];
            }
            
            // Optimized image finding
            let imageUrl = null;
            const imgElement = link.querySelector('img') || link.parentElement?.querySelector('img');
            if (imgElement) {
                imageUrl = imgElement.src || imgElement.dataset.src;
            }
            
            products.push({
                title: title.substring(0, 200), // Limit title length
                price: priceText,
                link: link.href,
                imageUrl: imageUrl
            });
        }
        
        return products;
        """)

        # Process products extracted by JavaScript
        for product in js_products:
            try:
                title = product.get('title', '').strip()
                price_text = product.get('price', '').strip()
                link = product.get('link', '').strip()
                image_url = product.get('imageUrl', None)
                
                # Validate product link - απλοποιημένος έλεγχος για ταχύτητα
                if not link or '/items/' not in link:
                    continue
                
                # Extract price - βελτιστοποιημένη έκδοση
                price = 0
                if price_text:
                    price_match = re.search(r'(\d+[.,]?\d*)', price_text.replace(' ', ''))
                    if price_match:
                        try:
                            price_str = price_match.group(1).replace(',', '.')
                            price = float(price_str)
                        except ValueError:
                            continue  # Παραλείπουμε αντί να καταγράφουμε σφάλμα για ταχύτητα
                
                # Check if price is within the specified range
                if (min_price is None or max_price is None) or (min_price <= price <= max_price):
                    # Παραλείπουμε τον έλεγχο διπλότυπων για απλοποίηση και ταχύτητα
                    # καθώς έχουμε ήδη ελέγξει στο JavaScript με το processedUrls Set
                    vendora_products.append((title, price, link, image_url))
                
            except Exception as e:
                continue  # Παραλείπουμε τα σφάλματα αντί να τα καταγράφουμε για ταχύτητα

        # Print diagnostic information
        safe_print(f"Total products found: {len(vendora_products)}")

    except Exception as e:
        safe_print("Vendora search error")
    finally:
        driver.quit()


def search_sources(search_term, min_price, max_price, max_pages=1):
    """Search across multiple sources."""
    try:
        min_price = float(min_price)
        max_price = float(max_price)
        max_pages = int(max_pages)
        
        # Create and start threads
        skroutz_thread = threading.Thread(target=search_skroutz, args=(search_term, min_price, max_price))
        insomnia_thread = threading.Thread(target=search_insomnia, args=(search_term, min_price, max_price, max_pages))
        vendora_thread = threading.Thread(target=search_vendora, args=(search_term, min_price, max_price))

        skroutz_thread.start()
        insomnia_thread.start()
        vendora_thread.start()

        skroutz_thread.join()
        insomnia_thread.join()
        vendora_thread.join()

        # Pre-allocate list with estimated size for better performance
        estimated_size = len(skroutz_products) + len(insomnia_products) + len(vendora_products)
        all_products = []
        all_products.reserve(estimated_size) if hasattr(all_products, 'reserve') else None  # Only in Python 3.12+

        # Streamlined filtering and conversion
        for source, products_list in [
            ("skroutz", skroutz_products), 
            ("insomnia", insomnia_products), 
            ("vendora", vendora_products)
        ]:
            for product_data in products_list:
                title, price, link = product_data[0], product_data[1], product_data[2]
                image_url = product_data[3] if len(product_data) > 3 else None
                
                if min_price <= price <= max_price:
                    all_products.append({
                        "title": title, 
                        "price": price, 
                        "link": link,
                        "source": source,
                        "imageUrl": image_url
                    })

        # Χρήση της TimSort (υλοποίηση της Python) άμεσα για καλύτερη απόδοση
        all_products.sort(key=lambda x: x['price'])
        
        return all_products

    except Exception as e:
        return []

# Script execution
if __name__ == "__main__":
    try:
        if len(sys.argv) < 4:
            print(json.dumps())
            sys.exit(1)
        
        search_term = sys.argv[1]
        min_price = sys.argv[2]
        max_price = sys.argv[3]
        
        max_pages = 1
        if len(sys.argv) >= 5:
            max_pages = sys.argv[4]
        
        # Streamlined processing and output
        results = search_sources(search_term, min_price, max_price, max_pages)
        
        # Immediate output instead of building string in memory first
        print(json.dumps(results, ensure_ascii=False))
        
    except Exception as e:
        error_details = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        
        sys.exit(1)