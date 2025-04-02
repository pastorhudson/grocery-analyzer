from pprint import pprint
import browser_cookie3
import os
import requests
import time

# Load cookies from your browser (Firefox in this example)
cookies = browser_cookie3.firefox()

def get_order_items(order_id):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0',
        'Accept': 'application/json',
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


def get_all_order_items(max_pages=100, delay=0.5, order_types=None, json_file=None):
    """
    Retrieves order items across pages and returns a list of dictionaries
    with detailed information about each item.

    Args:
        max_pages (int, optional): Maximum number of pages to fetch. If None, fetches all pages.
        delay (float, optional): Delay between requests in seconds to avoid rate limiting.
        order_types (list, optional): List of order types to fetch. Options: ['STORE', 'ONLINE'].
                                      If None, fetches both types.
        json_file (str, optional): Path to a JSON file containing order data. If provided,
                                   the function will use this file instead of making API requests.

    Returns:
        list: A list of dictionaries, each containing details about an order item
    """
    import requests
    import time
    import os
    import json
    import browser_cookie3

    # Check if we should use a JSON file instead of making API requests
    if json_file:
        return process_json_file(json_file)

    # Load cookies from your browser (Firefox in this example)
    cookies = browser_cookie3.firefox()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.target.com/orders',
        'x-api-key': os.environ.get('X_API_KEY'),
        'Origin': 'https://www.target.com',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'Priority': 'u=4',
    }

    # Set default order types if none provided
    if order_types is None:
        order_types = ['STORE', 'ONLINE']
    elif isinstance(order_types, str):
        order_types = [order_types]  # Convert single string to list

    all_items = []

    # Process each order type
    for order_type in order_types:
        print(f"Fetching {order_type} orders...")

        current_page = 1
        total_pages = None

        # In the get_all_order_items function
        while (total_pages is None or current_page <= total_pages) and (max_pages is None or current_page <= max_pages):
            # Define parameters for the current page
            params = {
                'page_number': str(current_page),
                'page_size': '10',
                'order_purchase_type': order_type,
                'pending_order': 'true',
                'shipt_status': 'true',
            }

            try:
                # Make the API request
                response = requests.get(
                    'https://api.target.com/guest_order_aggregations/v1/order_history',
                    params=params,
                    cookies=cookies,
                    headers=headers,
                )

                # Check if the request was successful
                if response.status_code != 200:
                    print(f"Error on page {current_page} for {order_type} orders: Status code {response.status_code}")

                    # Check for the specific invalid page number error
                    if response.status_code == 400:
                        try:
                            error_data = response.json()
                            if error_data.get("errors") and any(e.get("error_key") == "ERR_INVALID_PAGE_NUMBER" for e in
                                                                error_data.get("errors", [])):
                                print("Reached maximum allowed page number. Target API seems to have a 100-page limit.")
                                print(f"Successfully processed pages 1-{current_page - 1}")
                                break
                        except:
                            pass

                    # For other errors, just break
                    break

                # Parse the response
                data = response.json()

                # Set total_pages if this is the first request
                if total_pages is None:
                    total_pages = data.get('total_pages', 0)
                    if max_pages is None:
                        print(f"Found {total_pages} pages of {order_type} orders. Fetching all pages.")
                    else:
                        pages_to_fetch = min(max_pages, total_pages)
                        print(f"Found {total_pages} pages of {order_type} orders. Fetching {pages_to_fetch} pages.")

                # Process orders on this page
                for order in data.get('orders', []):
                    order_id = order.get('store_receipt_id') or order.get('order_id')
                    placed_date = order.get('placed_date')
                    store_id = order.get('store_id')
                    order_total = order.get('summary', {}).get('grand_total')

                    # For store orders, get detailed order information
                    detailed_order_data = None
                    if order_type == 'STORE' and order.get('store_receipt_id'):
                        try:
                            detailed_order_data = get_order_details(order.get('store_receipt_id'), cookies, headers)
                            # Process the detailed order data instead if available
                            if detailed_order_data and 'order_lines' in detailed_order_data:
                                process_detailed_order(detailed_order_data, order_id, placed_date, store_id,
                                                       order_total, order_type, all_items)
                                continue  # Skip the standard processing below
                        except Exception as e:
                            print(f"Failed to get detailed order data for {order_id}: {str(e)}")

                    # Process each item in the order (standard processing if detailed data not available)
                    for item in order.get('order_lines', []):
                        item_data = item.get('item', {})

                        # Extract product classification
                        product_classification = item_data.get('product_classification', {})

                        # Construct the image URL if available
                        image_url = None
                        if item_data.get('images') and item_data['images'].get('base_url') and item_data['images'].get(
                                'primary_image'):
                            image_url = item_data['images']['base_url'] + item_data['images']['primary_image']

                        # Handle HTML entities in description
                        description = item_data.get('description', '')
                        if description:
                            description = description.replace('&#38;', '&').replace('&#8482;', '™')

                        # Calculate total price
                        unit_price = 0.0
                        list_price = 0.0
                        total_price = 0.0

                        try:
                            unit_price = float(item_data.get('unit_price', 0))
                            list_price = float(item_data.get('list_price', 0))
                            quantity = int(item.get('quantity', 1))
                            total_price = list_price * quantity
                        except (ValueError, TypeError):
                            pass

                        # Create a dictionary with detailed item details
                        item_dict = {
                            'order_id': order_id,
                            'placed_date': placed_date,
                            'store_id': store_id,
                            'order_total': order_total,
                            'order_type': order_type,
                            'line_id': item.get('order_line_id'),
                            'unique_key': item.get('unique_key'),
                            'tcin': item_data.get('tcin'),
                            'dpci': item_data.get('dpci'),
                            'description': description,
                            'quantity': item.get('quantity') or item.get('original_quantity', 1),
                            'unit_price': unit_price,
                            'list_price': list_price,
                            'total_price': total_price,
                            'image_url': image_url,
                            'category': {
                                'merchandise_type': product_classification.get('merchandise_type_name'),
                                'product_type': product_classification.get('product_type_name'),
                                'product_subtype': product_classification.get('product_subtype_name')
                            },
                            'status': {
                                'code': item.get('status', {}).get('code'),
                                'key': item.get('status', {}).get('key'),
                                'date': item.get('status', {}).get('date')
                            }
                        }

                        all_items.append(item_dict)

                if max_pages is None:
                    print(f"Processed page {current_page}/{total_pages} for {order_type} orders")
                else:
                    pages_to_fetch = min(max_pages, total_pages)
                    print(f"Processed page {current_page}/{pages_to_fetch} for {order_type} orders")

                # Move to the next page
                current_page += 1

                # Add a delay to avoid rate limiting
                time.sleep(delay)

            except Exception as e:
                print(f"Error processing page {current_page} for {order_type} orders: {str(e)}")
                break

        print(f"Completed fetching {order_type} orders")

    print(f"Retrieved {len(all_items)} items from all order types")
    return all_items


def get_order_details(order_id, cookies, headers):
    """
    Gets detailed information for a specific order

    Args:
        order_id (str): The order ID to retrieve details for
        cookies: Browser cookies for authentication
        headers: HTTP headers for the request

    Returns:
        dict: Detailed order data
    """
    import requests

    params = {
        'subscription': 'false',
    }

    response = requests.get(
        f'https://api.target.com/guest_order_aggregations/v1/{order_id}/store_order_details',
        params=params,
        cookies=cookies,
        headers=headers,
    )

    if response.status_code != 200:
        raise Exception(f"Failed to get order details: {response.status_code}")

    return response.json()


def generate_llm_prompt(llm_data):
    """
    Generates a text prompt for LLM analysis based on the structured order data.

    Args:
        llm_data (dict): Structured data prepared for LLM analysis

    Returns:
        str: A detailed prompt describing the data and requesting analysis
    """
    # Extract summary data
    summary = llm_data["summary"]
    total_orders = summary["total_orders"]
    total_items = summary["total_items"]
    total_spend = summary["total_spend"]
    date_range = summary["date_range"]

    # Create the prompt
    prompt = f"""# Target Shopping Analysis

## Overview
I have collected data on my Target shopping history, including {total_orders} orders with {total_items} items, 
totaling ${total_spend:.2f} spent between {date_range["start"]} and {date_range["end"]}.

## Request
Please analyze this data and provide insights about my Target shopping habits. Specifically, I'd like to know:

1. **Spending Patterns**: How does my spending vary by month, day of week, and time of day?
2. **Frequent Purchases**: What items do I purchase most frequently?
3. **Repeat Purchases**: Which items do I consistently buy over time?
4. **Shopping Behavior**: Can you identify any patterns in when and where I shop?
5. **Recommendations**: Based on this data, what suggestions would you make to help me:
   - Save money
   - Optimize my shopping
   - Take advantage of potential deals

## Data Summary
- Total Orders: {total_orders}
- Total Items: {total_items}
- Total Spend: ${total_spend:.2f}
- Date Range: {date_range["start"]} to {date_range["end"]}

### Most Frequent Items
"""

    # Add most frequent items
    for idx, item in enumerate(summary["most_frequent_items"][:10], 1):
        prompt += f"{idx}. {item['description']} - Quantity: {item['quantity']} (${item['list_price']:.2f} each)\n"

    # Add spending patterns
    prompt += "\n## Spending Patterns\n"

    # By month
    prompt += "\n### By Month\n"
    for month, amount in sorted(llm_data["spending_patterns"]["by_month"].items()):
        prompt += f"- {month}: ${amount:.2f}\n"

    # By day of week
    prompt += "\n### By Day of Week\n"
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for day in days_order:
        if day in llm_data["spending_patterns"]["by_day_of_week"]:
            amount = llm_data["spending_patterns"]["by_day_of_week"][day]
            prompt += f"- {day}: ${amount:.2f}\n"

    # By time of day
    prompt += "\n### By Time of Day\n"
    time_order = ["Early Morning (12AM-6AM)", "Morning (6AM-12PM)", "Afternoon (12PM-6PM)", "Evening (6PM-12AM)"]
    for time in time_order:
        if time in llm_data["spending_patterns"]["by_time_of_day"]:
            amount = llm_data["spending_patterns"]["by_time_of_day"][time]
            prompt += f"- {time}: ${amount:.2f}\n"

    # Add store distribution if available
    if summary["store_distribution"]:
        prompt += "\n## Store Distribution\n"
        for store_id, count in sorted(summary["store_distribution"].items(), key=lambda x: x[1], reverse=True):
            prompt += f"- Store {store_id}: {count} orders\n"

    # Add repeat purchases section
    prompt += "\n## Repeat Purchases\n"
    for idx, item in enumerate(llm_data["repeat_purchases"][:10], 1):
        prompt += f"{idx}. {item['description']} - Bought {item['total_quantity']} times, Total: ${item['total_spent']:.2f}\n"

    # Add closing
    prompt += """
## Additional Analysis
Please provide any other insights or patterns you notice in the data that might be helpful.

Thank you!
"""

    return prompt

def process_json_file(json_file):
    """
    Process a JSON file containing order data and return a list of dictionaries
    with detailed information about each item.

    Args:
        json_file (str): Path to the JSON file

    Returns:
        list: A list of dictionaries, each containing details about an order item
    """
    import json

    try:
        # Read the JSON file
        with open(json_file, 'r') as f:
            orders_data = json.load(f)

        all_items = []

        # Process each order
        for order in orders_data:
            order_id = order.get('order_id')
            placed_date = order.get('placed_date')
            store_id = order.get('store_id')
            order_total = order.get('order_total')

            # Process items in this order
            for item in order.get('items', []):
                # Try to get detailed item information if this is a previously seen item
                item_details = find_item_details(item.get('tcin'), all_items)

                # Set default values
                unit_price = 0.0
                list_price = 0.0

                # If we have details from a previous occurrence of this item, use them
                if item_details:
                    unit_price = item_details.get('unit_price', 0.0)
                    list_price = item_details.get('list_price', 0.0)
                    dpci = item_details.get('dpci')
                    category = item_details.get('category', {})
                else:
                    # If no previous details, make educated guesses
                    dpci = None
                    category = {}

                    # If we have order total and a single item, we can estimate the price
                    if order_total and len(order.get('items', [])) == 1:
                        try:
                            order_total_float = float(order_total)
                            quantity = int(item.get('quantity', 1))
                            unit_price = list_price = round(order_total_float / quantity, 2)
                        except (ValueError, TypeError, ZeroDivisionError):
                            pass

                # Calculate the total price based on list price and quantity
                try:
                    quantity = int(item.get('quantity', 1))
                    total_price = list_price * quantity
                except (ValueError, TypeError):
                    total_price = 0.0

                # Handle HTML entities in description
                description = item.get('description', '')
                if description:
                    description = description.replace('&#38;', '&').replace('&#8482;', '™').replace('&#39;',
                                                                                                    "'").replace(
                        '&#34;', '"')

                # Create a dictionary with detailed item details
                item_dict = {
                    'order_id': order_id,
                    'placed_date': placed_date,
                    'store_id': store_id,
                    'order_total': order_total,
                    'order_type': 'STORE',  # Assume STORE as default
                    'line_id': item.get('line_number'),
                    'unique_key': None,
                    'tcin': item.get('tcin'),
                    'dpci': dpci,
                    'description': description,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'list_price': list_price,
                    'total_price': total_price,
                    'image_url': None,
                    'category': category,
                    'status': {
                        'code': None,
                        'key': None,
                        'date': placed_date
                    }
                }

                all_items.append(item_dict)

        print(f"Processed {len(all_items)} items from JSON file")
        return all_items

    except Exception as e:
        print(f"Error processing JSON file: {str(e)}")
        return []


def find_item_details(tcin, items_list):
    """
    Find details for an item with the same TCIN in the existing items list

    Args:
        tcin (str): The TCIN to search for
        items_list (list): The list of items to search in

    Returns:
        dict or None: The item details if found, None otherwise
    """
    if not tcin or not items_list:
        return None

    for item in items_list:
        if item.get('tcin') == tcin and item.get('unit_price') > 0:
            return item

    return None


def process_detailed_order(order_data, order_id, placed_date, store_id, order_total, order_type, all_items):
    """
    Process a detailed order's data and add its items to the all_items list

    Args:
        order_data (dict): The detailed order data
        order_id (str): The order ID
        placed_date (str): The date the order was placed
        store_id (str): The store ID
        order_total (str): The order total
        order_type (str): The order type (STORE or ONLINE)
        all_items (list): The list to add items to
    """
    for order_line in order_data.get('order_lines', []):
        item_data = order_line.get('item', {})

        # Extract product classification
        product_classification = item_data.get('product_classification', {})

        # Construct the image URL if available
        image_url = None
        if item_data.get('images') and item_data['images'].get('base_url') and item_data['images'].get('primary_image'):
            image_url = item_data['images']['base_url'] + item_data['images']['primary_image']

        # Handle HTML entities in description
        description = item_data.get('description', '')
        if description:
            description = description.replace('&#38;', '&').replace('&#8482;', '™')

        # Calculate total price
        unit_price = 0.0
        list_price = 0.0
        total_price = 0.0

        try:
            unit_price = float(item_data.get('unit_price', 0))
            list_price = float(item_data.get('list_price', 0))
            quantity = int(order_line.get('quantity', 1))
            total_price = list_price * quantity
        except (ValueError, TypeError):
            pass

        # Create a dictionary with detailed item details
        item_dict = {
            'order_id': order_id,
            'placed_date': placed_date,
            'store_id': store_id,
            'order_total': order_total,
            'order_type': order_type,
            'line_id': order_line.get('order_line_id'),
            'unique_key': order_line.get('unique_key'),
            'tcin': item_data.get('tcin'),
            'dpci': item_data.get('dpci'),
            'description': description,
            'quantity': order_line.get('quantity', 1),
            'unit_price': unit_price,
            'list_price': list_price,
            'total_price': total_price,
            'image_url': image_url,
            'category': {
                'merchandise_type': product_classification.get('merchandise_type_name'),
                'product_type': product_classification.get('product_type_name'),
                'product_subtype': product_classification.get('product_subtype_name')
            },
            'status': {
                'code': order_line.get('status', {}).get('code'),
                'key': order_line.get('status', {}).get('key'),
                'date': order_line.get('status', {}).get('date')
            }
        }

        all_items.append(item_dict)


def prepare_data_for_llm_analysis(items):
    """
    Prepares order data in a format suitable for LLM analysis.

    Args:
        items (list): List of order item dictionaries

    Returns:
        dict: Structured data ready for LLM analysis
    """
    import datetime
    from collections import defaultdict, Counter

    # Initialize structure
    llm_data = {
        "summary": {
            "total_orders": 0,
            "total_items": 0,
            "total_spend": 0.0,
            "date_range": {"start": None, "end": None},
            "most_frequent_items": [],
            "store_distribution": {}
        },
        "orders": [],
        "spending_patterns": {
            "by_month": defaultdict(float),
            "by_day_of_week": defaultdict(float),
            "by_time_of_day": defaultdict(float)
        },
        "repeat_purchases": []
    }

    # Track unique orders and TCINs
    unique_orders = {}  # Using dict to store order details, not just IDs
    tcin_counter = Counter()
    tcin_prices = {}  # Store price information for each TCIN

    # Track earliest and latest dates
    earliest_date = None
    latest_date = None

    # Process each item
    for item in items:
        # Parse date
        placed_date = datetime.datetime.fromisoformat(item['placed_date'].replace('Z', '+00:00'))

        # Update date range
        if earliest_date is None or placed_date < earliest_date:
            earliest_date = placed_date
        if latest_date is None or placed_date > latest_date:
            latest_date = placed_date

        # Track unique orders
        order_id = item['order_id']
        if order_id not in unique_orders:
            # Store order details
            unique_orders[order_id] = {
                "order_id": order_id,
                "placed_date": item['placed_date'],
                "store_id": item['store_id'],
                "order_total": item['order_total'],
                "items": []  # Will store items in this order
            }

            # Calculate order total
            try:
                order_total = float(item['order_total'])
                llm_data["summary"]["total_spend"] += order_total
            except (ValueError, TypeError):
                pass

            # Add to spending patterns
            month_key = placed_date.strftime("%Y-%m")
            day_key = placed_date.strftime("%A")
            hour = placed_date.hour

            if hour < 6:
                time_key = "Early Morning (12AM-6AM)"
            elif hour < 12:
                time_key = "Morning (6AM-12PM)"
            elif hour < 18:
                time_key = "Afternoon (12PM-6PM)"
            else:
                time_key = "Evening (6PM-12AM)"

            try:
                llm_data["spending_patterns"]["by_month"][month_key] += order_total
                llm_data["spending_patterns"]["by_day_of_week"][day_key] += order_total
                llm_data["spending_patterns"]["by_time_of_day"][time_key] += order_total
            except (ValueError, TypeError):
                pass

            # Store distribution
            store_id = item['store_id']
            if store_id:
                if store_id not in llm_data["summary"]["store_distribution"]:
                    llm_data["summary"]["store_distribution"][store_id] = 1
                else:
                    llm_data["summary"]["store_distribution"][store_id] += 1

        # Track price information for this TCIN
        tcin = item['tcin']
        if tcin and (tcin not in tcin_prices or item.get('unit_price', 0) > 0):
            tcin_prices[tcin] = {
                'unit_price': item.get('unit_price', 0),
                'list_price': item.get('list_price', 0)
            }

        # Add this item to its order's items list with price information
        unique_orders[order_id]["items"].append({
            "tcin": item['tcin'],
            "description": item['description'],
            "quantity": item.get('quantity', 1),
            "line_number": item.get('line_number'),
            "unit_price": item.get('unit_price', 0),
            "list_price": item.get('list_price', 0),
            "total_price": item.get('total_price', 0)
        })

        # Count TCINs for most frequent items
        if tcin:
            description = item['description']
            quantity = item.get('quantity', 1)
            tcin_counter[(tcin, description)] += quantity

    # Set summary values
    llm_data["summary"]["total_orders"] = len(unique_orders)
    llm_data["summary"]["total_items"] = sum(quantity for (_, _), quantity in tcin_counter.items())

    if earliest_date and latest_date:
        llm_data["summary"]["date_range"]["start"] = earliest_date.strftime("%Y-%m-%d")
        llm_data["summary"]["date_range"]["end"] = latest_date.strftime("%Y-%m-%d")

    # Get most frequent items with price information
    most_common = tcin_counter.most_common(20)
    for (tcin, description), quantity in most_common:
        price_info = tcin_prices.get(tcin, {'unit_price': 0, 'list_price': 0})
        llm_data["summary"]["most_frequent_items"].append({
            "tcin": tcin,
            "description": description,
            "quantity": quantity,
            "unit_price": price_info['unit_price'],
            "list_price": price_info['list_price']
        })

    # Add orders to the orders array
    llm_data["orders"] = list(unique_orders.values())

    # Sort orders by date (newest first)
    llm_data["orders"].sort(key=lambda x: x["placed_date"], reverse=True)

    # Find repeat purchases (items bought multiple times)
    repeat_items = [(tcin, desc) for (tcin, desc), count in tcin_counter.items() if count > 1]
    for tcin, description in repeat_items:
        # Find all instances of this item
        purchases = []
        total_spent = 0.0

        for order in llm_data["orders"]:
            for item in order["items"]:
                if item["tcin"] == tcin:
                    purchases.append({
                        "order_id": order["order_id"],
                        "date": order["placed_date"],
                        "quantity": item["quantity"],
                        "unit_price": item.get("unit_price", 0),
                        "total_price": item.get("total_price", 0)
                    })
                    total_spent += item.get("total_price", 0)

        if len(purchases) > 1:
            price_info = tcin_prices.get(tcin, {'unit_price': 0, 'list_price': 0})
            llm_data["repeat_purchases"].append({
                "tcin": tcin,
                "description": description,
                "total_quantity": tcin_counter[(tcin, description)],
                "unit_price": price_info['unit_price'],
                "list_price": price_info['list_price'],
                "total_spent": total_spent,
                "purchases": purchases
            })

    # Sort repeat purchases by frequency
    llm_data["repeat_purchases"].sort(key=lambda x: x["total_quantity"], reverse=True)

    # Convert defaultdicts to regular dicts for JSON serialization
    llm_data["spending_patterns"]["by_month"] = dict(llm_data["spending_patterns"]["by_month"])
    llm_data["spending_patterns"]["by_day_of_week"] = dict(llm_data["spending_patterns"]["by_day_of_week"])
    llm_data["spending_patterns"]["by_time_of_day"] = dict(llm_data["spending_patterns"]["by_time_of_day"])

    return llm_data


def save_data_for_llm(items, output_file='target_data_for_llm.json', prompt_file='target_llm_prompt.txt',
                      orders_file='target_orders.json'):
    """
    Processes order data and saves both the structured data and a text prompt for LLM analysis.

    Args:
        items (list): List of order item dictionaries
        output_file (str): File name for the JSON structured data
        prompt_file (str): File name for the text prompt
        orders_file (str): File name for just the orders data

    Returns:
        tuple: (data_path, prompt_path, orders_path) - Paths to the created files
    """
    import json

    # Prepare the data
    llm_data = prepare_data_for_llm_analysis(items)

    # Generate the prompt
    prompt = generate_llm_prompt(llm_data)

    # Save structured data to JSON
    with open(output_file, 'w') as f:
        json.dump(llm_data, f, indent=2)

    # Save prompt to text file
    with open(prompt_file, 'w') as f:
        f.write(prompt)

    # Save just the orders data to a separate file
    with open(orders_file, 'w') as f:
        json.dump(llm_data.get('orders', []), f, indent=2)

    print(f"Saved structured data to {output_file}")
    print(f"Saved LLM prompt to {prompt_file}")
    print(f"Saved just orders data to {orders_file}")

    return output_file, prompt_file, orders_file


# Example usage:
if __name__ == "__main__":
    # Option 1: Get all orders from the API
    # Note: cookies and x-api-key need to be defined before calling this function
    all_items = get_all_order_items()

    # Option 2: Parse a saved JSON file
    # all_items = parse_existing_json_file('target_orders.json')

    # Process the data for LLM analysis
    data_file, prompt_file, orders_file = save_data_for_llm(all_items)
    #
    print(f"\nData prepared successfully for LLM analysis!")
    print(
        f"To analyze your Target shopping habits, upload the prompt file ({prompt_file}) to an LLM like ChatGPT or Claude.")
    #
    # # Print a sample of the items
    print("\nSample of your shopping data:")
    for item in all_items[:5]:
        print(f"Order: {item['order_id']} - {item['description']} (Qty: {item['quantity']})")
