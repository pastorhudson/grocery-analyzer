import os
from pprint import pprint

import requests
import browser_cookie3

# Load cookies from your browser (Firefox in this example)
cookies = browser_cookie3.firefox()

def get_order(order_id):

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0',
        'x-api-key': os.environ.get('X_API_KEY'),
    }

    params = {
        'subscription': 'false',
    }

    response = requests.get(
        f'https://api.target.com/guest_order_aggregations/v1/{order_id}/store_order_details',
        params=params,
        cookies=cookies,
        headers=headers,
    )

    return response.json()


def extract_order_items(order_data):
    """
    Extract items from an order and return a list of dictionaries with item data.

    Args:
        order_data (dict): The JSON order data

    Returns:
        list: A list of dictionaries containing item data
    """
    items_list = []

    # Loop through each order line in the order
    for order_line in order_data.get('order_lines', []):
        # Get the item data from the order line
        item_data = order_line.get('item', {})

        # Create a dictionary with the relevant item information
        item_dict = {
            'order_line_id': order_line.get('order_line_id'),
            'quantity': order_line.get('quantity'),
            'tcin': item_data.get('tcin'),
            'description': item_data.get('description', ''),
            'unit_price': item_data.get('unit_price'),
            'list_price': item_data.get('list_price'),
            'dpci': item_data.get('dpci', ''),
            'status': order_line.get('status', {}).get('key', '')
        }

        # Add any product classification if available
        if 'product_classification' in item_data:
            classification = item_data['product_classification']
            item_dict['product_type'] = classification.get('product_type_name', '')
            item_dict['product_subtype'] = classification.get('product_subtype_name', '')

        # Add any image information if available
        if 'images' in item_data:
            images = item_data['images']
            item_dict['image_url'] = images.get('base_url', '') + images.get('primary_image', '')

        items_list.append(item_dict)

    return items_list


# Example usage
def get_items_from_order(order_id):
    order_data = get_order(order_id)

    return extract_order_items(order_data)


if __name__ == '__main__':
    order_id = '5092-2184-0157-7882'
    pprint(get_items_from_order(order_id))