import axios from 'axios';

const API_URL = '';

export const getProducts = async () => {
    const response = await axios.get(`${API_URL}/products`);
    return response.data;
};

export const getProductHistory = async (productId) => {
    const response = await axios.get(`${API_URL}/products/${productId}/history`);
    return response.data;
};

export const triggerScrape = async () => {
    const response = await axios.post(`${API_URL}/scrape`);
    return response.data;
};
