# Παράλληλη Αναζήτηση Προϊόντων

Μια web-based πλατφόρμα που επιτρέπει στους χρήστες να πραγματοποιούν παράλληλη αναζήτηση μεταχειρισμένων προϊόντων σε πολλαπλές ιστοσελίδες (Vendora, Insomnia, Skroutz, Skoop).

## Λειτουργίες

- Αναζήτηση προϊόντων με λέξη-κλειδί
- Φιλτράρισμα με βάση το εύρος τιμών
- Παράλληλη αναζήτηση σε πολλαπλές πηγές
- Προβολή αποτελεσμάτων ταξινομημένων κατά τιμή
- Φιλτράρισμα αποτελεσμάτων ανά πηγή

## Τεχνολογίες

- Frontend: React, TypeScript, Tailwind CSS
- Backend: Python (Selenium για web scraping)
- API: Python HTTP Server

## Εγκατάσταση και Εκτέλεση

### Προαπαιτούμενα

- Node.js
- Python 3
- Firefox (για το Selenium)
- Geckodriver (για το Selenium)

### Εγκατάσταση

1. Εγκαταστήστε τις εξαρτήσεις του frontend:
   ```
   npm install
   ```

2. Εγκαταστήστε τις εξαρτήσεις του Python:
   ```
   pip install selenium
   ```

### Εκτέλεση

1. Εκκινήστε τον API server:
   ```
   python api/search.py
   ```

2. Εκκινήστε την εφαρμογή React:
   ```
   npm run dev
   ```

3. Ανοίξτε τον browser στη διεύθυνση που εμφανίζεται στο terminal.

## Χρήση

1. Εισάγετε το προϊόν που θέλετε να αναζητήσετε
2. Ορίστε το εύρος τιμών (ελάχιστη και μέγιστη τιμή)
3. Πατήστε το κουμπί "Αναζήτηση"
4. Περιμένετε να ολοκληρωθεί η αναζήτηση
5. Δείτε τα αποτελέσματα ταξινομημένα κατά τιμή
6. Χρησιμοποιήστε τις καρτέλες για να φιλτράρετε τα αποτελέσματα ανά πηγή

## Σημειώσεις

- Η εφαρμογή χρησιμοποιεί το Selenium για web scraping, το οποίο απαιτεί Firefox και Geckodriver
- Η αναζήτηση μπορεί να διαρκέσει μερικά δευτερόλεπτα, ανάλογα με τον αριθμό των αποτελεσμάτων
- Τα αποτελέσματα ταξινομούνται αυτόματα κατά τιμή (από τη χαμηλότερη στην υψηλότερη)