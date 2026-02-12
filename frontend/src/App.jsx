import { useEffect, useState } from 'react';
import axios from 'axios';
import ProductChart from './components/ProductChart';
import { RefreshCw, Search, Tag } from 'lucide-react';

const App = () => {
    const [products, setProducts] = useState([]);
    const [selectedProduct, setSelectedProduct] = useState(null);
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(false);
    const [scraping, setScraping] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [filterType, setFilterType] = useState('All');
    const [sortBy, setSortBy] = useState('default');

    const fetchProducts = async () => {
        setLoading(true);
        try {
            const res = await axios.get('/products');
            setProducts(res.data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };
    
    useEffect(() => {
        fetchProducts();
    }, []);
    
    const handleScrape = async () => {
        setScraping(true);
        try {
            await axios.post('/scrape');
            setTimeout(fetchProducts, 5000); 
        } catch (err) {
            console.error(err);
        } finally {
            setTimeout(() => setScraping(false), 2000);
        }
    };
    
    const viewProduct = async (product) => {
        if (selectedProduct?.id === product.id) {
            setSelectedProduct(null);
            setHistory([]);
            return;
        }
        
        setSelectedProduct(product);
        try {
            const res = await axios.get(`/products/${product.id}/history`);
            setHistory(res.data);
        } catch (err) {
            console.error(err);
        }
    };

    const filteredProducts = products
        .filter(p => {
            const matchesSearch = p.name.toLowerCase().includes(searchTerm.toLowerCase());
            if (!matchesSearch) return false;

            if (filterType === 'Lowest Price (€)') return p.is_lowest_all_time;
            if (filterType === 'Discounted (%)') return p.discount_percentage > 0;
            if (filterType === 'Price OK') return p.is_price_ok;
            
            return true;
        })
        .sort((a, b) => {
            if (sortBy === 'discount_desc') return b.discount_percentage - a.discount_percentage;
            if (sortBy === 'price_asc') return (a.current_price || 0) - (b.current_price || 0);
            if (sortBy === 'price_desc') return (b.current_price || 0) - (a.current_price || 0);
            if (sortBy === 'name_asc') return a.name.localeCompare(b.name);
            return 0;
        });

    return (
        <div className="min-h-screen bg-gray-900 text-white p-6 font-sans">
            <header className="flex flex-col md:flex-row justify-between items-center mb-10 gap-4">
                <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-gradient-to-tr from-purple-500 to-pink-500 rounded-lg flex items-center justify-center text-2xl font-bold shadow-lg shadow-purple-500/30">
                        B
                    </div>
                    <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-pink-600">
                        Bernabei Tracker
                    </h1>
                </div>

                <div className="flex items-center gap-4 w-full md:w-auto relative">
                    <Search className="absolute left-3 w-5 h-5 text-gray-400" />
                    <input 
                        type="text" 
                        placeholder="Search wines..." 
                        className="bg-gray-800 border border-gray-700 rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500 w-full md:w-64"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                    <button 
                        onClick={handleScrape}
                        disabled={scraping}
                        className={`flex items-center gap-2 px-6 py-2 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 rounded-lg transition-all shadow-lg shadow-blue-500/20 font-medium whitespace-nowrap ${scraping ? 'opacity-75 cursor-not-allowed' : ''}`}
                    >
                        <RefreshCw className={`w-5 h-5 ${scraping ? 'animate-spin' : ''}`} />
                        {scraping ? 'Updating...' : 'Update Prices'}
                    </button>
                </div>
            </header>

            {/* Filter Bar */}
            <div className="flex flex-col md:flex-row justify-between items-center bg-gray-800 p-4 rounded-xl mb-6 shadow-lg border border-gray-700 gap-4">
                <div className="flex items-center gap-2 overflow-x-auto w-full md:w-auto pb-2 md:pb-0">
                    <span className="text-gray-400 text-sm font-medium mr-2 whitespace-nowrap bg-gray-900 px-3 py-1 rounded-lg border border-gray-700">
                        {filteredProducts.length} / {products.length}
                    </span>
                    {['All', 'Lowest Price (€)', 'Discounted (%)', 'Price OK'].map(filter => (
                        <button
                            key={filter}
                            onClick={() => setFilterType(filter)}
                            className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                                filterType === filter 
                                ? 'bg-purple-600 text-white' 
                                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                            }`}
                        >
                            {filter}
                        </button>
                    ))}
                </div>
                
                <div className="flex items-center gap-2 w-full md:w-auto">
                    <span className="text-gray-400 text-sm whitespace-nowrap">Sort by:</span>
                    <select 
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value)}
                        className="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg focus:ring-purple-500 focus:border-purple-500 block w-full p-2.5"
                    >
                        <option value="default">Default</option>
                        <option value="discount_desc">Discount % (High to Low)</option>
                        <option value="price_asc">Price (Low to High)</option>
                        <option value="price_desc">Price (High to Low)</option>
                        <option value="name_asc">Name (A-Z)</option>
                    </select>
                </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {filteredProducts.map(product => (
                    <div key={product.id} className="bg-gray-800 rounded-xl p-0 hover:shadow-2xl hover:shadow-purple-500/10 transition-all border border-gray-700 overflow-hidden flex flex-col group">
                        <div className="h-48 bg-white p-4 flex items-center justify-center relative overflow-hidden">
                            {product.image_url ? (
                                <img 
                                    src={product.image_url} 
                                    alt={product.name} 
                                    className="h-full object-contain transform group-hover:scale-110 transition-transform duration-300" 
                                />
                            ) : (
                                <div className="text-gray-400">No Image</div>
                            )}
                            <div className="absolute top-2 right-2 flex flex-col gap-1 items-end">
                                {product.is_lowest_all_time && (
                                    <span className="bg-yellow-500 text-black text-xs font-bold px-2 py-1 rounded-full shadow-md flex items-center gap-1">
                                        <Tag size={12} /> €
                                    </span>
                                )}
                                {product.discount_percentage > 0 && (
                                    <span className="bg-red-500 text-white text-xs font-bold px-2 py-1 rounded-full shadow-md">
                                        -{product.discount_percentage}%
                                    </span>
                                )}
                                {product.is_price_ok && (
                                    <span className="bg-green-500 text-white text-xs font-bold px-2 py-1 rounded-full shadow-md">
                                        Prezzo OK
                                    </span>
                                )}
                            </div>
                        </div>
                        
                        <div className="p-5 flex-1 flex flex-col">
                            <div className="mb-4 flex-1">
                                <h2 className="text-lg font-semibold mb-1 line-clamp-2 leading-tight text-gray-100 group-hover:text-purple-400 transition-colors">
                                    {product.name}
                                </h2>
                                <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">
                                    {product.category?.replace(/\//g, ' ').trim() || 'Wine'}
                                </p>
                            </div>
                            
                            <div className="flex items-end justify-between mb-4">
                                <div className="flex flex-col">
                                    <span className="text-sm text-gray-400">Current Price</span>
                                    <div className="flex items-baseline gap-2">
                                        <span className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-emerald-500">
                                            €{product.current_price?.toFixed(2) || 'N/A'}
                                        </span>
                                        {/* Optional: Show original price if discounted? We don't have max price in product model directly, but discount implies it. */}
                                    </div>
                                </div>
                                <a 
                                    href={product.product_link} 
                                    target="_blank" 
                                    rel="noopener noreferrer" 
                                    className="text-xs text-blue-400 hover:text-blue-300 transition-colors bg-blue-900/30 px-2 py-1 rounded"
                                >
                                    Visit Store ↗
                                </a>
                            </div>

                            <button 
                                onClick={() => viewProduct(product)}
                                className={`w-full py-2 rounded-lg text-sm font-medium transition-all ${
                                    selectedProduct?.id === product.id 
                                    ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/25' 
                                    : 'bg-gray-700 hover:bg-gray-600 text-gray-200'
                                }`}
                            >
                                {selectedProduct?.id === product.id ? 'Hide History' : 'View Price History'}
                            </button>
                        </div>
                        
                        {selectedProduct?.id === product.id && (
                            <div className="p-4 bg-gray-800 border-t border-gray-700 animate-in fade-in slide-in-from-top-4">
                                <div className="flex justify-between items-center mb-2">
                                    <h3 className="text-sm font-medium text-gray-400">Price Trend</h3>
                                    <span className="text-xs text-gray-500">Last 30 Days</span>
                                </div>
                                <ProductChart history={history} />
                            </div>
                        )}
                    </div>
                ))}
            </div>
            
            {products.length === 0 && !loading && (
                <div className="flex flex-col items-center justify-center py-20 text-gray-500">
                    <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mb-4">
                        <Tag className="w-8 h-8 opacity-50" />
                    </div>
                    <h3 className="text-xl font-medium mb-2">No products tracked yet</h3>
                    <p className="max-w-md text-center mb-6">
                        Click the "Update Prices" button to start scraping products from Bernabei.it. 
                        This might take a minute.
                    </p>
                    <button 
                        onClick={handleScrape}
                        className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
                    >
                        Start First Scrape
                    </button>
                </div>
            )}

            {loading && (
                <div className="flex justify-center py-20">
                     <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
                </div>
            )}
        </div>
    );
};

export default App;
