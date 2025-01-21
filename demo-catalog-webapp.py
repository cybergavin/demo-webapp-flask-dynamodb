from flask import Flask, request, jsonify, render_template_string
import boto3
import os
from botocore.exceptions import ClientError

# Initialize Flask app
app = Flask(__name__)

# AWS DynamoDB configuration
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table_name = "ProductCatalog"

def init_dynamodb():
    """Initialize the DynamoDB table."""
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'id', 'KeyType': 'HASH'}  # Partition key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'id', 'AttributeType': 'S'}
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        table.wait_until_exists()
    except ClientError as e:
        if e.response['Error']['Code'] != 'ResourceInUseException':
            raise

# Initialize DynamoDB and seed data
init_dynamodb()

HOME_PAGE = """<!doctype html>
<html>
<head>
    <title>Product Catalog</title>
</head>
<body>
    <h1>Demo Product Catalog</h1>
    <p>This application allows you to perform CRUD operations on a product catalog.</p>
    <ul>
        <li><a href="/products">View All Products</a></li>
        <li><a href="/create-product">Create a New Product</a></li>
    </ul>
</body>
</html>"""

CREATE_PRODUCT_PAGE = """<!doctype html>
<html>
<head>
    <title>Create Product</title>
</head>
<body>
    <h1>Create a New Product</h1>
    <form action="/products" method="post">
        <label for="name">Name:</label><br>
        <input type="text" id="name" name="name" required><br>
        <label for="description">Description:</label><br>
        <input type="text" id="description" name="description"><br>
        <label for="price">Price:</label><br>
        <input type="number" id="price" name="price" step="0.01" required><br><br>
        <input type="submit" value="Create">
    </form>
    <p><a href="/">Back to Home</a></p>
</body>
</html>"""

@app.route("/")
def home():
    """Display the home page."""
    return HOME_PAGE

@app.route("/create-product", methods=["GET"])
def create_product_form():
    """Display the form to create a new product."""
    return CREATE_PRODUCT_PAGE

@app.route("/products", methods=["GET"])
def get_products():
    """Fetch all products and display them in a table."""
    table = dynamodb.Table(table_name)
    response = table.scan()
    products = response.get('Items', [])

    products_table = """<!doctype html>
    <html>
    <head>
        <title>Products</title>
    </head>
    <body>
        <h1>Product List</h1>
        <table border="1">
            <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Description</th>
                <th>Price</th>
                <th>Actions</th>
            </tr>
    """

    for p in products:
        products_table += f"""<tr>
            <td>{p['id']}</td>
            <td>{p['name']}</td>
            <td>{p['description']}</td>
            <td>{float(p['price']):.2f}</td>
            <td>
                <form action="/delete-product/{p['id']}" method="post" style="display:inline;">
                    <button type="submit">Delete</button>
                </form>
                <form action="/update-product/{p['id']}" method="get" style="display:inline;">
                    <button type="submit">Edit</button>
                </form>
            </td>
        </tr>"""

    products_table += """</table>
        <form action="/delete-all-products" method="post">
            <button type="submit">Delete All Products</button>
        </form>
        <p><a href="/">Back to Home</a></p>
    </body>
    </html>"""

    return products_table

@app.route("/products", methods=["POST"])
def create_product():
    """Create a new product from form input."""
    name = request.form.get("name")
    description = request.form.get("description")
    price = request.form.get("price")

    if not name or not price:
        return "Name and price are required", 400

    try:
        price = float(price)
    except ValueError:
        return "Invalid price", 400

    product_id = os.urandom(4).hex()
    table = dynamodb.Table(table_name)
    table.put_item(Item={"id": product_id, "name": name, "description": description, "price": str(price)})

    return "<p>Product created successfully!</p><p><a href='/'>Back to Home</a></p>"

@app.route("/delete-product/<string:product_id>", methods=["POST"])
def delete_product(product_id):
    """Delete a specific product."""
    table = dynamodb.Table(table_name)
    table.delete_item(Key={"id": product_id})
    return "<p>Product deleted successfully!</p><p><a href='/products'>Back to Products</a></p>"

@app.route("/delete-all-products", methods=["POST"])
def delete_all_products():
    """Delete all products from the catalog."""
    table = dynamodb.Table(table_name)
    response = table.scan()
    with table.batch_writer() as batch:
        for item in response.get('Items', []):
            batch.delete_item(Key={"id": item['id']})

    return "<p>All products deleted successfully!</p><p><a href='/products'>Back to Products</a></p>"

@app.route("/update-product/<string:product_id>", methods=["GET", "POST"])
def update_product(product_id):
    """Update a specific product."""
    table = dynamodb.Table(table_name)

    if request.method == "GET":
        response = table.get_item(Key={"id": product_id})
        product = response.get('Item')

        if not product:
            return "<p>Product not found!</p><p><a href='/products'>Back to Products</a></p>", 404

        return f"""<!doctype html>
        <html>
        <head>
            <title>Update Product</title>
        </head>
        <body>
            <h1>Update Product</h1>
            <form action="/update-product/{product_id}" method="post">
                <label for='name'>Name:</label><br>
                <input type='text' id='name' name='name' value='{product['name']}' required><br>
                <label for='description'>Description:</label><br>
                <input type='text' id='description' name='description' value='{product['description']}'><br>
                <label for='price'>Price:</label><br>
                <input type='number' id='price' name='price' step='0.01' value='{product['price']}' required><br><br>
                <input type='submit' value='Update'>
            </form>
            <p><a href='/products'>Back to Products</a></p>
        </body>
        </html>"""

    elif request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        price = request.form.get("price")

        if not name or not price:
            return "Name and price are required", 400

        try:
            price = float(price)
        except ValueError:
            return "Invalid price", 400

        table.update_item(
            Key={"id": product_id},
            UpdateExpression="SET #n = :name, description = :description, price = :price",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={":name": name, ":description": description, ":price": str(price)}
        )

        return "<p>Product updated successfully!</p><p><a href='/products'>Back to Products</a></p>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)