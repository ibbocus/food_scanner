import React, { useState } from "react";
import { BarcodeScannerComponent } from "./components/BarcodeScannerComponent";
import { ProductCard } from "./components/ProductCard";

export default function App() {
  const [barcode, setBarcode] = useState(null);
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleDetected = async (code) => {
    if (code && code !== barcode) {
      setBarcode(code);
      setLoading(true);
      try {
        const res = await fetch("https://qzaauchdr8.execute-api.eu-west-2.amazonaws.com/dev/request", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ barcode: code })
        });
        const data = await res.json();
        setProduct(data.product || {});
      } catch (err) {
        console.error("Failed to fetch product info", err);
        setProduct(null);
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <h1 className="text-3xl font-bold text-center mb-4">Food Scanner 🍜</h1>
      <div className="max-w-xl mx-auto">
        <BarcodeScannerComponent onDetected={handleDetected} />
        {loading && <p className="text-center text-blue-500 mt-4">Looking up barcode...</p>}
        {product && <ProductCard product={product} />}
      </div>
    </div>
  );
}