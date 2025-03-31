import React, { useState, useEffect, useRef } from 'react';
import { Search, ShoppingBag, ExternalLink, Loader2, X, ArrowUp, ArrowDown, Image as ImageIcon } from 'lucide-react';
import './AnimatedInput.css'; 
import './AnimatedButton.css';
import './loader.css';
import './tracking-animation.css';

interface Product {
  title: string;
  price: number;
  link: string;
  source: string;
  imageUrl?: string;
}

function App() {
  const [searchTerm, setSearchTerm] = useState('');
  const [minPrice, setMinPrice] = useState(0);
  const [maxPrice, setMaxPrice] = useState(10000);
  const [maxPages, setMaxPages] = useState(1);
  const [isSearching, setIsSearching] = useState(false);
  const [products, setProducts] = useState<Product[]>([]);
  const [error, setError] = useState('');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [showSearchForm, setShowSearchForm] = useState(true);
  const abortControllerRef = useRef<AbortController | null>(null);
 
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!searchTerm.trim()) {
      setError('Παρακαλώ εισάγετε ένα προϊόν για αναζήτηση');
      return;
    }

    if (minPrice >= maxPrice) {
      setError('Η ελάχιστη τιμή πρέπει να είναι μικρότερη από τη μέγιστη');
      return;
    }

    if (maxPages < 1) {
      setError('Ο αριθμός σελίδων πρέπει να είναι τουλάχιστον 1');
      return;
    }

    setError('');
    setIsSearching(true);
    setProducts([]);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      const response = await fetch(`/search?searchTerm=${encodeURIComponent(searchTerm)}&minPrice=${minPrice}&maxPrice=${maxPrice}&maxPages=${maxPages}`, {
        signal: abortController.signal
      });
      
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      if (data.error) throw new Error(data.error);
      
      setProducts(data);
      setIsSearching(false);
      setShowSearchForm(false);
    } catch (err) {
      if (err.name === 'AbortError') {
        setError('Η αναζήτηση ακυρώθηκε');
      } else {
        console.error('Search error:', err);
        setError('Σφάλμα κατά την αναζήτηση. Παρακαλώ δοκιμάστε ξανά.');
      }
      setIsSearching(false);
    }
  };

  const handleCancelSearch = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setIsSearching(false);
    setError('Η αναζήτηση ακυρώθηκε');
  };

  const handleNewSearch = () => {
    setProducts([]);
    setShowSearchForm(true);
    setError('');
  };

  const toggleSortOrder = () => {
    setSortOrder(prevOrder => prevOrder === 'asc' ? 'desc' : 'asc');
  };

  const skroutzProducts = products
    .filter(product => product.source.toLowerCase() === 'skroutz')
    .sort((a, b) => sortOrder === 'asc' ? a.price - b.price : b.price - a.price);

  const insomniaProducts = products
    .filter(product => product.source.toLowerCase() === 'insomnia')
    .sort((a, b) => sortOrder === 'asc' ? a.price - b.price : b.price - a.price);

  const vendoraProducts = products
    .filter(product => product.source.toLowerCase() === 'vendora')
    .sort((a, b) => sortOrder === 'asc' ? a.price - b.price : b.price - a.price);

  const handleImageError = (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
    e.currentTarget.src = '/api/placeholder/80/80';
    e.currentTarget.classList.add('opacity-50');
  };

  const renderProductCard = (product: Product) => (
    <div 
      className="p-3 hover:bg-white/5 transition-colors group rounded-xl border border-white/10 h-full flex flex-col"
    >
      <div className="flex items-center gap-3">
        <div className="relative w-25 h-24 flex-shrink-0 flex items-center justify-center bg-white/5 rounded-lg border border-white/10 overflow-hidden group-hover:border-gray-200 transition-all duration-200 group-hover:scale-105 group-hover:shadow-lg group-hover:shadow-gray-500/20">
          {product.imageUrl ? (
            <img 
              src={product.imageUrl} 
              alt={product.title}
              className="object-contain w-full h-full transition-transform duration-200 group-hover:scale-110"
              onError={handleImageError}
            />
          ) : (
            <ImageIcon className="text-gray-200 transition-transform duration-200 group-hover:scale-110" size={16} />
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-gray-500/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
        </div>

        <div className="flex-1">
          <h3 className="text-base font-medium line-clamp-2">{product.title}</h3>
          <div className="text-base font-bold text-green-200 mt-1">
            €{product.price.toFixed(2)}
          </div>
        </div>
      </div>

      <div className="mt-auto pt-2 flex justify-end">
        <a
          href={product.link}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center text-gray-200 hover:text-white transition-colors group text-sm"
        >
          Προβολή
          <ExternalLink className="ml-1 group-hover:translate-x-1 transition-transform" size={12} />
        </a>
      </div>
    </div>
  );

  return (
    <div 
      className="text-white min-h-screen"
      id="your-element-selector"
    >
      <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0zNiAxOGMzLjMxIDAgNiAyLjY5IDYgNnMtMi42OSA2LTYgNi02LTIuNjktNi02IDIuNjktNiA2LTZ6TTI0IDQ4YzMuMzEgMCA2IDIuNjkgNiA2cy0yLjY5IDYtNiA2LTYtMi42OS02LTYgMi42OS02IDYtNnptMC0xMmMzLjMxIDAgNiAyLjY5IDYgNnMtMi42OSA2LTYgNi02LTIuNjktNi02IDIuNjktNiA2LTZ6IiBzdHJva2U9IiNmZmYiIHN0cm9rZS1vcGFjaXR5PSIuMDUiLz48L2c+PC9zdmc+')] opacity-10 pointer-events-none"></div>

      <div className="relative z-10 w-full px-4 py-12">
        <header className={`text-center ${showSearchForm ? 'mb-16' : 'mb-8'}`}>
          <div className="inline-flex items-center justify-center p-3 bg-white/10 rounded-2xl mb-6">
            <ShoppingBag className="text-gray-200" size={32} />
          </div>
          <h1 className="text-5xl text-gray-200 mb-2 font-bold mb-4 tracking-in-contract">
            Product Compass
          </h1>
          <p className="text-lg text-gray-200 max-w-2xl mx-auto">
            Εξερευνήστε και συγκρίνετε τιμές προϊόντων από πολλαπλές πλατφόρμες
          </p>
        </header>

        {showSearchForm ? (
        <div className="max-w-3xl mx-auto">
          <form onSubmit={handleSearch} className="space-y-6">
            <div className="input-container">
              <input
                type="text"
                placeholder="Αναζήτηση προϊόντων..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="animated-input"
              />
            </div>

            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="block text-sm text-gray-200 mb-2">Ελάχιστη Τιμή</label>
                <div className="input-container">
                  <input
                    type="number"
                    placeholder="0"
                    value={minPrice}
                    onChange={(e) => setMinPrice(Number(e.target.value))}
                    
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm text-gray-200 mb-2">Μέγιστη Τιμή</label>
                <div className="input-container">
                  <input
                    type="number"
                    placeholder="10000"
                    value={maxPrice}
                    onChange={(e) => setMaxPrice(Number(e.target.value))}
                    className="animated-input"
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="block text-sm text-gray-200 mb-2">
                Βάθος Αναζήτησης (Αριθμός Σελίδων)
              </label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="1"
                  max="10"
                  step="1"
                  className="flex-grow h-2 bg-white/10 rounded-lg cursor-pointer"
                  value={maxPages}
                  onChange={(e) => setMaxPages(Number(e.target.value))}
                />
                <span className="bg-white/5 text-white px-4 py-2 rounded-xl min-w-[60px] text-center border border-white/20">
                  {maxPages}
                </span>
              </div>
              <p className="text-xs text-gray-200 mt-2">
                Περισσότερες σελίδες = Περισσότερα αποτελέσματα, αλλά πιο αργή αναζήτηση
              </p>
            </div>

            {error && (
              <div className="bg-red-500/20 text-red-200 p-4 rounded-xl text-center border border-red-500/30">
                {error}
              </div>
            )}

{isSearching ? (
  <div className="relative w-full flex justify-center items-center">
    <div className="wrapper">
      <div className="circle"></div>
      <div className="circle"></div>
      <div className="circle"></div>
      <div className="shadow"></div>
      <div className="shadow"></div>
      <div className="shadow"></div>
    </div>
    
    <div className="absolute top-full mt-4 flex justify-center w-full">
      <button 
        type="button"
        onClick={handleCancelSearch}
        className="px-6 py-4 bg-red-500/20 hover:bg-red-500/30 rounded-xl transition-colors flex items-center"
      >
        <X className="mr-2" /> Ακύρωση
      </button>
    </div>
  </div>
) : (
              <button
                type="submit"
                className="w-full mx-auto py-4 rounded-xl transition-all animated button"
              >
                <span>Start</span>
                <div className="top"></div>
                <div className="left"></div>
                <div className="bottom"></div>
                <div className="right"></div>
              </button>
            )}
          </form>
        </div>
        ) : (
          <div className="text-center mb-8">
            <button
              onClick={handleNewSearch}
              className="inline-flex items-center px-8 py-4 rounded-xl transition-all"
            >
              <Search className="mr-2" />
              Αναζητήστε ξανά
            </button>
          </div>
        )}

        {products.length > 0 && !showSearchForm && (
          <div className="mt-8 px-4 w-full">
            <div className="mx-auto w-full max-w-full">
              <div className="px-4 py-6 mb-4 flex justify-between items-center bg-white/5 rounded-xl border border-white/20">
                <h2 className="text-2xl font-semibold">
                  Βρέθηκαν {products.length} προϊόντα
                </h2>
                <button 
                  onClick={toggleSortOrder}
                  className="flex items-center text-gray-100 mb-2 hover:text-white transition-colors"
                >
                  {sortOrder === 'asc' ? (
                    <>
                      <ArrowUp className="mr-2" /> Αύξουσα
                    </>
                  ) : (
                    <>
                      <ArrowDown className="mr-2" /> Φθίνουσα
                    </>
                  )}
                </button>
              </div>

              <div className="grid grid-cols-3 gap-8 w-full max-w-full">
                {/* Skroutz Column */}
                <div className="bg-white/5 rounded-3xl border border-white/20 overflow-hidden flex flex-col">
                  <div className="px-4 py-3 border-b border-white/10 bg-gradient-to-r from-gray-500/20 to-gray-500/5">
                    <h3 className="text-lg font-semibold flex items-center">
                      <div className="bg-gray-500/30 rounded-full p-1 mr-2">
                        <Search size={12} className="text-gray-200" />
                      </div>
                      Skroutz 
                      <span className="ml-2 text-sm text-gray-200 font-normal">
                        ({skroutzProducts.length})
                      </span>
                    </h3>
                  </div>
                  
                  <div className="flex-grow overflow-y-auto max-h-[600px] p-2 space-y-2">
                    {skroutzProducts.length > 0 ? (
                      skroutzProducts.map((product, index) => (
                        <div key={`skroutz-${index}`}>
                          {renderProductCard(product)}
                        </div>
                      ))
                    ) : (
                      <div className="h-full flex items-center justify-center text-gray-200 text-center p-4">
                        Δεν βρέθηκαν προϊόντα από το Skroutz
                      </div>
                    )}
                  </div>
                </div>

                {/* Insomnia Column */}
                <div className="bg-white/5 rounded-3xl border border-white/20 overflow-hidden flex flex-col">
                  <div className="px-4 py-3 border-b border-white/10 bg-gradient-to-r from-blue-500/20 to-blue-500/5">
                    <h3 className="text-lg font-semibold flex items-center">
                      <div className="bg-blue-500/30 rounded-full p-1 mr-2">
                        <Search size={12} className="text-blue-200" />
                      </div>
                      Insomnia
                      <span className="ml-2 text-sm text-blue-200 font-normal">
                        ({insomniaProducts.length})
                      </span>
                    </h3>
                  </div>
                  
                  <div className="flex-grow overflow-y-auto max-h-[600px] p-2 space-y-2">
                    {insomniaProducts.length > 0 ? (
                      insomniaProducts.map((product, index) => (
                        <div key={`insomnia-${index}`}>
                          {renderProductCard(product)}
                        </div>
                      ))
                    ) : (
                      <div className="h-full flex items-center justify-center text-blue-200 text-center p-4">
                        Δεν βρέθηκαν προϊόντα από το Insomnia
                      </div>
                    )}
                  </div>
                </div>

                {/* Vendora Column */}
                <div className="bg-white/5 rounded-3xl border border-white/20 overflow-hidden flex flex-col">
                  <div className="px-4 py-3 border-b border-white/10 bg-gradient-to-r from-pink-500/20 to-pink-500/5">
                    <h3 className="text-lg font-semibold flex items-center">
                      <div className="bg-pink-500/30 rounded-full p-1 mr-2">
                        <Search size={12} className="text-pink-200" />
                      </div>
                      Vendora
                      <span className="ml-2 text-sm text-pink-200 font-normal">
                        ({vendoraProducts.length})
                      </span>
                    </h3>
                  </div>
                  
                  <div className="flex-grow overflow-y-auto max-h-[600px] p-2 space-y-2">
                    {vendoraProducts.length > 0 ? (
                      vendoraProducts.map((product, index) => (
                        <div key={`vendora-${index}`}>
                          {renderProductCard(product)}
                        </div>
                      ))
                    ) : (
                      <div className="h-full flex items-center justify-center text-pink-200 text-center p-4">
                        Δεν βρέθηκαν προϊόντα από το Vendora
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;