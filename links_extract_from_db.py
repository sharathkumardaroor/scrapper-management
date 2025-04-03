import sqlite3
import tkinter as tk
from tkinter import filedialog, ttk
import csv
from bs4 import BeautifulSoup
import os
from urllib.parse import urlparse, urljoin
from tqdm import tqdm  # For progress bar

def extract_links_from_html(html_content, base_url=None):
    """Extract all unique links from HTML content"""
    if not html_content:
        return set()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    links = set()
    
    for tag in soup.find_all(['a', 'img', 'script', 'link', 'iframe']):
        if tag.name == 'a' and tag.has_attr('href'):
            url = tag['href'].strip()
        elif tag.name == 'img' and tag.has_attr('src'):
            url = tag['src'].strip()
        elif tag.name == 'script' and tag.has_attr('src'):
            url = tag['src'].strip()
        elif tag.name == 'link' and tag.has_attr('href'):
            url = tag['href'].strip()
        elif tag.name == 'iframe' and tag.has_attr('src'):
            url = tag['src'].strip()
        else:
            continue
            
        # Skip empty URLs and javascript/anchor links
        if not url or url.startswith(('javascript:', 'mailto:', 'tel:', '#')):
            continue
            
        # Make URL absolute if base_url is provided
        if base_url:
            url = urljoin(base_url, url)
            
        # Normalize URL
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:  # Proper URL
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        else:
            clean_url = url
        
        links.add(clean_url)
    
    return links

def select_db_file():
    """Open file dialog to select SQLite database file"""
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select SQLite Database File",
        filetypes=[("SQLite Database", "*.db *.sqlite *.sqlite3"), ("All Files", "*.*")]
    )
    return file_path

def get_table_info(db_path):
    """Get list of tables and their columns in the database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in cursor.fetchall()]
        
        # Get columns for each table
        table_columns = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table});")
            columns = [column[1] for column in cursor.fetchall()]
            table_columns[table] = columns
        
        return tables, table_columns
    except Exception as e:
        print(f"Error reading database: {e}")
        return [], {}
    finally:
        if 'conn' in locals():
            conn.close()

def select_table_and_column(tables, table_columns):
    """Create GUI to select table and column"""
    root = tk.Tk()
    root.title("Select Table and Column")
    
    # Table selection
    tk.Label(root, text="Select Table:").pack(pady=5)
    table_var = tk.StringVar(root)
    table_dropdown = ttk.Combobox(root, textvariable=table_var, values=tables, state="readonly")
    table_dropdown.pack(pady=5)
    
    # Column selection
    tk.Label(root, text="Select HTML Column:").pack(pady=5)
    column_var = tk.StringVar(root)
    column_dropdown = ttk.Combobox(root, textvariable=column_var, state="readonly")
    column_dropdown.pack(pady=5)
    
    # Base URL entry
    tk.Label(root, text="Base URL (optional, for relative links):").pack(pady=5)
    base_url_var = tk.StringVar(root)
    tk.Entry(root, textvariable=base_url_var, width=50).pack(pady=5)
    
    # Batch size for progress updates
    tk.Label(root, text="Batch size for progress (rows):").pack(pady=5)
    batch_var = tk.StringVar(root, value="1000")
    tk.Entry(root, textvariable=batch_var).pack(pady=5)
    
    # Result variable
    result = {'table': None, 'column': None, 'base_url': None, 'batch_size': 1000}
    
    def update_columns(*args):
        selected_table = table_var.get()
        if selected_table in table_columns:
            column_dropdown['values'] = table_columns[selected_table]
            if column_dropdown['values']:
                column_dropdown.current(0)
    
    table_var.trace('w', update_columns)
    
    def on_submit():
        try:
            result['batch_size'] = int(batch_var.get())
        except ValueError:
            result['batch_size'] = 1000
        
        result['table'] = table_var.get()
        result['column'] = column_var.get()
        result['base_url'] = base_url_var.get() or None
        root.quit()
    
    tk.Button(root, text="Extract Links", command=on_submit).pack(pady=10)
    
    # Initialize with first table if available
    if tables:
        table_dropdown.current(0)
        update_columns()
    
    root.mainloop()
    root.destroy()
    
    return result if result['table'] and result['column'] else None

def get_row_count(db_path, table):
    """Get the number of rows in the table"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        return cursor.fetchone()[0]
    except Exception as e:
        print(f"Error getting row count: {e}")
        return 0
    finally:
        if 'conn' in locals():
            conn.close()

def extract_links_from_db(db_path, table, column, base_url=None, batch_size=1000):
    """Extract all unique links from the specified table and column with progress bar"""
    total_rows = get_row_count(db_path, table)
    if total_rows == 0:
        print("Table is empty or doesn't exist.")
        return []
    
    all_links = set()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Use a generator to fetch rows in batches
        def batch_fetcher():
            offset = 0
            while True:
                cursor.execute(f"SELECT {column} FROM {table} LIMIT {batch_size} OFFSET {offset};")
                batch = cursor.fetchall()
                if not batch:
                    break
                yield batch
                offset += batch_size
        
        # Process with progress bar
        with tqdm(total=total_rows, desc="Processing rows", unit="row") as pbar:
            for batch in batch_fetcher():
                for row in batch:
                    if row[0]:  # Check if content is not None or empty
                        links = extract_links_from_html(row[0], base_url)
                        all_links.update(links)
                pbar.update(len(batch))
        
        return sorted(all_links)
    except Exception as e:
        print(f"Error extracting links: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def save_to_csv(links, output_path=None):
    """Save links to CSV file"""
    if not links:
        print("No links to save.")
        return None
    
    if not output_path:
        root = tk.Tk()
        root.withdraw()
        initial_file = f"extracted_links_{len(links)}.csv"
        output_path = filedialog.asksaveasfilename(
            title="Save Links as CSV",
            defaultextension=".csv",
            initialfile=initial_file,
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
    
    if output_path:
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Extracted Links"])
                for link in links:
                    writer.writerow([link])
            return output_path
        except Exception as e:
            print(f"Error saving CSV: {e}")
    return None

def main():
    print("Step 1: Select SQLite database file")
    db_path = select_db_file()
    if not db_path:
        print("No file selected. Exiting.")
        return
    
    print("\nStep 2: Select table and column")
    tables, table_columns = get_table_info(db_path)
    if not tables:
        print("No tables found in the database. Exiting.")
        return
    
    selection = select_table_and_column(tables, table_columns)
    if not selection:
        print("No table/column selected. Exiting.")
        return
    
    print("\nStep 3: Extracting links...")
    links = extract_links_from_db(
        db_path, 
        selection['table'], 
        selection['column'], 
        selection['base_url'],
        selection['batch_size']
    )
    
    print(f"\nFound {len(links)} unique links.")
    if links:
        print("\nSample links:")
        for link in links[:5]:
            print(f" - {link}")
        if len(links) > 5:
            print(" - ...")
    
    print("\nStep 4: Save links to CSV file")
    output_path = save_to_csv(links)
    if output_path:
        print(f"\nLinks saved to: {os.path.abspath(output_path)}")
    else:
        print("Links not saved.")

if __name__ == "__main__":
    # Install tqdm if not available
    try:
        from tqdm import tqdm
    except ImportError:
        print("Installing tqdm for progress bar...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "tqdm"])
        from tqdm import tqdm
    
    main()