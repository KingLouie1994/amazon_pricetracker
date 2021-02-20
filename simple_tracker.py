# Imports from the amazon_config file
from amazon_config import(get_web_driver_options, get_chrome_web_driver, set_ignore_certificate_error,
                          set_browser_as_incognito, NAME, CURRENCY, FILTERS, BASE_URL, DIRECTORY)

# Imports from third party libraries
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
import json
import time
from datetime import datetime


# Creating a class that scrapes all needed information from the Base URL
class AmazonAPI:
    # Initialising all values needed
    def __init__(self, search_term, filters, base_url, currency):
        self.search_term = search_term
        self.filters = f"&rh=p_36%3A{filters['min']}00-{filters['max']}00"
        self.base_url = base_url
        self.currency = currency
        options = get_web_driver_options()
        self.driver = get_chrome_web_driver(options)
        set_ignore_certificate_error(options)
        set_browser_as_incognito(options)

    def get_products_links(self):
        # Open the browser and go to Base URL
        self.driver.get(self.base_url)
        # Find searchbar
        element = self.driver.find_element_by_xpath(
            '//*[@id="twotabsearchtextbox"]')
        # Type in search term
        element.send_keys(self.search_term)
        # Start search
        element.send_keys(Keys.ENTER)
        time.sleep(2)
        # Set filters
        self.driver.get(f'{self.driver.current_url}{self.filters}')
        print(f"Our url: {self.driver.current_url}")
        time.sleep(2)
        # Create a list of all results found on base URL fitting our filters
        result_list = self.driver.find_elements_by_class_name('s-result-list')
        links = []
        try:
            results = result_list[0].find_elements_by_xpath(
                "//div/span/div/div/div[2]/div[2]/div/div[1]/div/div/div[1]/h2/a")
            links = [link.get_attribute('href') for link in results]
            return links
        except Exception as e:
            print("Didn't get any products...")
            print(e)
            return links

    # Function to cut out the product Id (in this case ASIN: Amazon Standard Identification Number) out of link
    def get_asin(self, product_link):
        return product_link[product_link.find('/dp/') + 4:product_link.find('/ref')]

    # Using function that cuts out product Id (in this case ASIN: Amazon Standard Identification Number) on all returned link
    def get_asins(self, links):
        return [self.get_asin(link) for link in links]

    # Function to create the essential link needed to find product
    def shorten_url(self, asin):
        return self.base_url + 'dp/' + asin

    # Getting the title of the product from every link returned
    def get_title(self):
        try:
            return self.driver.find_element_by_id('productTitle').text
        except Exception as e:
            print(e)
            print(f"Can't get title of a product - {self.driver.current_url}")
            return None

    # Getting the seller of the product from every link returned
    def get_seller(self):
        try:
            return self.driver.find_element_by_id('bylineInfo').text
        except Exception as e:
            print(e)
            print(f"Can't get seller of a product - {self.driver.current_url}")
            return None

    # Function to convert the price in good readable format in get_price()
    def convert_price(self, price):
        price = price.split(self.currency)[1]
        try:
            price = price.split("\n")[0] + "." + price.split("\n")[1]
        except:
            Exception()
        try:
            price = price.split(",")[0] + price.split(",")[1]
        except:
            Exception()
        return float(price)

    # Getting the price of the product from every link returned
    def get_price(self):
        price = None
        try:
            price = self.driver.find_element_by_id('priceblock_ourprice').text
            price = self.convert_price(price)
        except NoSuchElementException:
            try:
                availability = self.driver.find_element_by_id(
                    'availability').text
                if 'Available' in availability:
                    price = self.driver.find_element_by_class_name(
                        'olp-padding-right').text
                    price = price[price.find(self.currency):]
                    price = self.convert_price(price)
            except Exception as e:
                print(e)
                print(
                    f"Can't get price of a product - {self.driver.current_url}")
                return None
        except Exception as e:
            print(e)
            print(f"Can't get price of a product - {self.driver.current_url}")
            return None
        return price

    # Function that runs the functions to get information for single product
    def get_single_product_info(self, asin):
        print(f"Product ID: {asin} - getting data...")
        product_short_url = self.shorten_url(asin)
        self.driver.get(f'{product_short_url}?language=en_GB')
        time.sleep(2)
        title = self.get_title()
        seller = self.get_seller()
        price = self.get_price()
        if title and seller and price:
            product_info = {
                'asin': asin,
                'url': product_short_url,
                'title': title,
                'seller': seller,
                'price': price
            }
            return product_info
        return None

    # Calling the function that gets information about the product on all returned links
    def get_products_info(self, links):
        asins = self.get_asins(links)
        products = []
        for asin in asins:
            product = self.get_single_product_info(asin)
            if product:
                products.append(product)
        return products

    # Function that first calls the function to get all relevant links and then get the information from these links
    def run(self):
        print('Starting script...')
        print(f"Looking for {self.search_term} products...")
        # Get all relevant links
        links = self.get_products_links()
        time.sleep(1)
        # Default if no links can be found
        if not links:
            print('Stopped script.')
            return
        # Printing the information how many links found
        print(f"Got {len(links)} links to products...")
        print("Getting info about products...")
        # Getting information from all links
        products = self.get_products_info(links)
        # Close browser when everything is done
        self.driver.quit()
        # Return products to create Report
        return products


class GenerateReport:
    # Initialising all values needed
    def __init__(self, file_name, filters, base_link, currency, data):
        self.data = data
        self.file_name = file_name
        self.filters = filters
        self.base_link = base_link
        self.currency = currency
        report = {
            'title': self.file_name,
            # Function defined later to calculate the date the report is created
            'date': self.get_now(),
            # Function defined later to sort products to find lowest price
            'best_item': self.get_best_item(),
            'currency': self.currency,
            'filters': self.filters,
            'base_link': self.base_link,
            'products': self.data
        }
        print("Creating report...")
        # Open file and input the json data received from AmazonAPI class!
        with open(f'{DIRECTORY}/{file_name}.json', 'w') as f:
            json.dump(report, f)
        print("Done...")

    # Calculate date the report is created
    def get_now(self):
        # Using datetime from datetime library
        now = datetime.now()
        return now.strftime("%d/%m/%Y %H:%M:%S")

    # Function to sort products to find lowest price
    def get_best_item(self):
        try:
            return sorted(self.data, key=lambda k: k['price'])[0]
        except Exception as e:
            # Code runs if sorting fails
            print(e)
            print("Problem with sorting items")
            return None


if __name__ == '__main__':
    amazon = AmazonAPI(NAME, FILTERS, BASE_URL, CURRENCY)
    data = amazon.run()
    print(len(data))
    GenerateReport(NAME, FILTERS, BASE_URL, CURRENCY, data)
