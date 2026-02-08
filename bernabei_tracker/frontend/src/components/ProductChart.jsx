import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const ProductChart = ({ history }) => {
    // Format timestamp
    const data = history.map(item => ({
        ...item,
        formattedDate: new Date(item.timestamp).toLocaleDateString()
    }));

    return (
        <div className="w-full h-64 mt-4">
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="formattedDate" />
                    <YAxis />
                    <Tooltip />
                    <Line type="monotone" dataKey="price" stroke="#8884d8" name="Price (€)" />
                    {data.some(d => d.ordinary_price) && (
                        <Line type="monotone" dataKey="ordinary_price" stroke="#82ca9d" name="Ordinary (€)" strokeDasharray="5 5" />
                    )}
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
};

export default ProductChart;
