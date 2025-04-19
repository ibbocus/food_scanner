export function ProductCard({ product }) {
  const {
    product_name,
    image_url,
    nutriments = {}
  } = product || {};

  const {
    energy_100g,
    fat_100g,
    sugars_100g,
    proteins_100g,
    salt_100g
  } = nutriments;

  return (
    <div className="bg-white shadow-lg rounded-lg mt-6 overflow-hidden">
      {image_url && (
        <img
          src={image_url}
          alt={product_name || "Product"}
          className="w-full max-h-96 object-contain bg-white"
        />
      )}
      <div className="p-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">
          {product_name || "Unknown Product"}
        </h2>
        <ul className="space-y-2 text-gray-700">
          <li><strong>Energy:</strong> {energy_100g || 0} kcal</li>
          <li><strong>Fat:</strong> {fat_100g || 0} g</li>
          <li><strong>Sugars:</strong> {sugars_100g || 0} g</li>
          <li><strong>Proteins:</strong> {proteins_100g || 0} g</li>
          <li><strong>Salt:</strong> {salt_100g || 0} g</li>
        </ul>
      </div>
    </div>
  );
}

