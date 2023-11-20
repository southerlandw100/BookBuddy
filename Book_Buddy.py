from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import scrolledtext
from tkinter import font
import webbrowser
import threading

chrome_options = Options()
chrome_options.add_argument("--log-level=3")
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920x1080")
url_label = None  
search_status_label = None  
result_url_label = None
hyperlink_label = None
books = []
processed_isbns = set()


###***Functions and class declaration***###
class Book:
    def __init__(self, title, isbn):
        self.title = title
        self.isbn = isbn

    def __str__(self):
        return f" '{self.title}' (ISBN: {self.isbn})"

def scrape_and_display_books(url):
    global books, processed_isbns, status_label
    status_label.config(text="Generating your bookshelf... This may take a few moments...")
    root.update_idletasks()

    try:
        browser = webdriver.Chrome(options=chrome_options)
        browser.get(url)

        WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'my rating')]")))
        scroll_attempts = 0
        max_scroll_attempts = 10

        while scroll_attempts < max_scroll_attempts:
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            sleep(3)
            scroll_attempts += 1

        soup = BeautifulSoup(browser.page_source, 'html.parser')
        isbn_element = soup.find_all('td', class_='field isbn')

        for elem in isbn_element:
            isbn_value = elem.find('div', class_='value').get_text(strip=True)
            if isbn_value not in processed_isbns:
                title_element = elem.find_previous_sibling('td', class_='field title')
                title_link = title_element.find('a')
                title_value = title_link.get_text(strip=True) if title_link else 'No title found'
                books.append(Book(title_value, isbn_value))
                processed_isbns.add(isbn_value)

        browser.quit()
        books_display.delete(1.0, tk.END)
        for book in books:
            books_display.insert(tk.END, str(book) + '\n')

        status_label.config(text="Here is your bookshelf:")
        root.update_idletasks()
        if books:
            book_select_label.grid()
            book_select_entry.grid()
            max_price_label.grid()
            max_price_entry.grid()
            search_button.grid()

    except Exception as e:
        print(f"An error occurred: {e}")
        status_label.config(text="Error- please ensure the URL was entered properly.")

def on_scrape_button_clicked():
    url = url_entry.get()
    scrape_and_display_books(url)

def find_book_by_title(title, books):
    return next((book for book in books if book.title.lower() == title.lower()), None)

def on_search_button_clicked():
    # Clear any existing messages
    search_status_label.config(text="", fg='black')  # Resetting the color if it was changed to red due to an error

    book_title = book_select_entry.get()
    max_price = max_price_entry.get()

    selected_book = find_book_by_title(book_title, books)
    if selected_book:
        try:
            max_price_float = float(max_price)
            if max_price_float < 0:
                raise ValueError("Price cannot be negative.")
            
            # Show searching status
            search_status_label.config(text="Searching for books...")
            root.update_idletasks()  # Update the GUI to show the searching status
            
            # Perform the search operation
            threading.Thread(target=search_and_display_results, args=(selected_book.isbn, max_price_float)).start()
        except ValueError as e:
            search_status_label.config(text=f"Invalid input: {e}", fg='red')
    else:
        search_status_label.config(text="Book not found. Please make sure to enter the exact title.", fg='red')

def search_and_display_results(isbn, max_price):
    results_url = search_on_addall(isbn, max_price)
    
    # The following operations affect the GUI, so they need to be run in the main thread
    root.after(0, display_search_results, results_url)

def display_search_results(results_url):
    global hyperlink_label, status_label

    # Remove the 'Searching for books...' message
    search_status_label.config(text="")

    if "sorry, can't find" in results_url.lower():
        status_label.config(text="Sorry, no results matched your book and price. Please try again.", fg='red')
    else:
        # Display the hyperlink for the results
        display_url(results_url)


def open_url(url):
    webbrowser.open(url)

# create the hyperlink 
def display_url(url):
    global hyperlink_label, status_label

    # Clear the search status label
    search_status_label.config(text="")

    # Clear any previous hyperlink
    if hyperlink_label:
        hyperlink_label.grid_remove()

    # If there's a valid URL, create a new hyperlink label
    if url and url != "no_results" and url != "error":
        hyperlink_label = tk.Label(root, text="Click here for all the books we found!", fg="blue", cursor="hand2", font=('Arial', 12))
        hyperlink_label.grid(row=20, column=0, sticky='w', padx=(90))
        hyperlink_label.bind("<Button-1>", lambda e: open_url(url))
    elif url == "no_results":
        search_status_label.config(text="Sorry, no results matched your book and price. Please try again.", fg='red')
        search_status_label.grid()
    elif url == "error":
        search_status_label.config(text="Error occurred during search. Please try again.", fg='red')
        search_status_label.grid()

# driving ISBN and max price data on addall to return a hyperlink of books
def search_on_addall(isbn, max_price):
    try:
        search_browser = webdriver.Chrome(options=chrome_options)
        search_browser.get('https://www.addall.com/used/')
        WebDriverWait(search_browser, 10).until(EC.element_to_be_clickable((By.ID, "showadvanced"))).click()
        search_bar = search_browser.find_element(By.NAME, 'isbn')
        search_bar.send_keys(isbn)
        max_price_field = search_browser.find_element(By.NAME, 'max')
        max_price_field.clear()
        max_price_field.send_keys(str(max_price))
        search_bar.send_keys(Keys.RETURN)
        WebDriverWait(search_browser, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Check if no results were found
        page_source = search_browser.page_source
        if "Sorry, can't find" in page_source:
            search_browser.quit()
            return "no_results"

        results_url = search_browser.current_url
        search_browser.quit()
        return results_url
    except Exception as e:
        print(f"Error in searching: {e}")
        return "error"


########******GUI building zone*****#########
root = tk.Tk()
root.geometry("720x890")
root.title("Book Buddy")

label = tk.Label(root, text="Welcome to Book Buddy!", font=('Arial', 18), justify='center')
label.grid(row=0, column=0)

# Define the font with underline
underline_font = font.Font(root, family='Arial', size=12, underline=True)
instructions0 = tk.Label(root, text="Instructions", font=underline_font)
instructions0.grid(row=1, column=0, sticky='w')

instructions1 = tk.Label(root, text="1) Ensure you have a Goodreads account with a bookshelf containing your books, and a stable\n     internet connection.", font=('Arial', 12), justify='left')
instructions1.grid(row=2, column=0, sticky='w')

instructions2 = tk.Label(root, text="2) Input the complete URL from the 'All' section of your Goodreads bookshelf for accurate results.", font=('Arial', 12), justify='left')
instructions2.grid(row=3, column=0, sticky='w')

instructions3 = tk.Label(root, text="3) After scraping, your bookshelf list will display below. To find a specific book, type its\n     exact title in the search box.\n   Note- make sure the book you have selected has an associated ISBN.  If it does not, then you will\n     have to search manually.", font=('Arial', 12), justify='left')
instructions3.grid(row=4, column=0, sticky='w')

instructions4 = tk.Label(root, text="4) Specify your maximum budget for the book (excluding shipping and handling costs) to see\n     available listings within your price range.", font=('Arial', 12), justify='left')
instructions4.grid(row=5, column=0, sticky='w')

instructions5 = tk.Label(root, text="5) Find your book, make your purchase, and enjoy reading!", font=('Arial', 12))
instructions5.grid(row=6, column=0, sticky='w')

url_label = tk.Label(root, text="Enter your Goodreads bookshelf URL:", font=('Arial', 12))
url_label.grid(row=7, column=0, sticky='w')

url_entry = tk.Entry(root, font=('Arial', 12))
url_entry.grid(row=8, column=0, sticky='w', padx=(90))

scrape_button = tk.Button(root, text="Scrape Bookshelf", command=on_scrape_button_clicked)
scrape_button.grid(row=10, column=0, sticky='w', padx=(90))

status_label = tk.Label(root, text="", font=('Arial', 12))
status_label.grid(row=11, column=0, columnspan=2, sticky='w')

books_display = scrolledtext.ScrolledText(root, wrap='word', height=10, width=75)
books_display.grid(row=12, column=0, sticky='nsw')

book_select_label = tk.Label(root, text="Enter a book title:", font=('Arial', 12))
book_select_label.grid(row=14, column=0, sticky='w')
book_select_label.grid_remove()

book_select_entry = tk.Entry(root, font=('Arial', 12))
book_select_entry.grid(row=15, column=0, sticky='w', padx=(90))
book_select_entry.grid_remove()

max_price_label = tk.Label(root, text="Enter the max price you are willing to pay before shipping and handling costs:", font=('Arial', 12))
max_price_label.grid(row=16, column=0, sticky='w')
max_price_label.grid_remove()

max_price_entry = tk.Entry(root, font=('Arial', 12))
max_price_entry.grid(row=17, column=0, sticky='w', padx=(90))
max_price_entry.grid_remove()

search_button = tk.Button(root, text="Search for Book", command=on_search_button_clicked)
search_button.grid(row=18, column=0, sticky='w', padx=(90))
search_button.grid_remove()

search_status_label = tk.Label(root, text="", font=('Arial', 12))
search_status_label.grid(row=19, column=0, sticky='w', padx=(90))
search_status_label.grid_remove()  # Hide initially

# Use padx and pady for uniform spacing and alignment
for widget in root.winfo_children():
    widget.grid_configure(padx=10, pady=5)

root.mainloop()