import React from "react";

export function ProductCard({ product }) {
  return (
    <div className="bg-white shadow rounded p-4">
      <h2 className="text-xl font-semibold mb-2">{product.product_name || "Unnamed Product"}</h2>
      {product.image_url && (
        <img src={product.image_url} alt={product.product_name} className="w-full h-auto rounded mb-2" />
      )}
      {product.ingredients_text && (
        <p className="text-sm text-gray-700"><strong>Ingredients:</strong> {product.ingredients_text}</p>
      )}
      {product.nutriments && (
        <div className="mt-2">
          <p className="text-sm"><strong>Energy:</strong> {product.nutriments["energy-kcal"]} kcal</p>
          <p className="text-sm"><strong>Fat:</strong> {product.nutriments.fat} g</p>
          <p className="text-sm"><strong>Sugars:</strong> {product.nutriments.sugars} g</p>
          <p className="text-sm"><strong>Proteins:</strong> {product.nutriments.proteins} g</p>
          <p className="text-sm"><strong>Salt:</strong> {product.nutriments.salt} g</p>
        </div>
      )}
    </div>
  );
}
