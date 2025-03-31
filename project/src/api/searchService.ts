import axios from 'axios';

interface Product {
  title: string;
  price: number;
  link: string;
  source: string;
}

export const searchProducts = async (
  searchTerm: string, 
  minPrice: number, 
  maxPrice: number
): Promise<Product[]> => {
  try {
    console.log('Searching with parameters:', { searchTerm, minPrice, maxPrice });
    
    const response = await axios.get('/search', {
      params: {
        searchTerm,
        minPrice,
        maxPrice
      }
    });
    
    console.log('Search results:', response.data);
    return response.data;
  } catch (error) {
    console.error('Detailed search error:', error);
    
    if (axios.isAxiosError(error)) {
      // More detailed error logging for Axios errors
      console.error('Error response:', error.response?.data);
      console.error('Error status:', error.response?.status);
    }
    
    throw error;
  }
};