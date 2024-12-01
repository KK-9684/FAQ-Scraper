import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import threading
import tkinter as tk
from tkinter import messagebox

def get_page_with_retry(url, options, retries=3, delay=5):
    for attempt in range(retries):
        try:
            page = requests.get(url, **options)
            page.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            return page
        except (requests.exceptions.RequestException, requests.exceptions.ReadTimeout) as e:
            print(f"Attempt {attempt+1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay)  # Wait before retrying
            else:
                raise  # Reraise the exception after all retries have failed

def scrape_website(url, textarea, cancel_event):
    # Init question, answer, category, and QA list
    site = url
    options = {
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        },
        'timeout': 10  # Increased timeout to 30 seconds
    }
    questions = []
    answers = []
    categoriePaths = []
    qaPaths = []

    textarea.delete('1.0', tk.END)
    textarea.insert(tk.END, "開始\n")
    textarea.yview(tk.END)
    
    # Send the request and parse the homepage
    try:
        page = get_page_with_retry(site, options)
        soup = BeautifulSoup(page.content, 'html.parser')
        aTagList = soup.find_all('a')  # Find all anchor tags in the homepage

        # Loop through all anchor tags and check their href for category paths
        for aTag in aTagList:
            aPath = aTag.get('href')
            if aPath and '/category/show/' in aPath:  # If 'href' contains '/category/show/'
                if (aPath and site in aPath):
                    categoriePaths.append(aPath)
                else:
                    categoriePaths.append(site + aPath)

        # If categories are found, proceed to scrape them
        if categoriePaths:
            categoriePaths = list(set(categoriePaths))
            textarea.insert(tk.END, f"カテゴリー : {len(categoriePaths)}\n")
            textarea.yview(tk.END)
            for cPath in categoriePaths:
                if cancel_event.is_set():
                    return
                time.sleep(1)
                cPage = get_page_with_retry(cPath, options)
                cSoup = BeautifulSoup(cPage.content, 'html.parser')        
                # Look for question paths in the category page
                cATagList = cSoup.find_all('a')
                for cATag in cATagList:
                    cAPath = cATag.get('href')
                    if cAPath and '/faq/show/' in cAPath:  # If 'href' contains '/faq/show/'
                        if (cAPath and site in cAPath):
                            qaPaths.append(cAPath)
                        else:
                            qaPaths.append(site + cAPath)
        else:
            # If no category paths, directly search for questions in the homepage
            for aTag in aTagList:
                aPath = aTag.get('href')
                if aPath and '/faq/show/' in aPath:  # If 'href' contains '/faq/show/'
                    if (aPath and site in aPath):
                        qaPaths.append(aPath)
                    else:
                        qaPaths.append(site + aPath)

        # If question paths are found, scrape the questions and answers
        if qaPaths:
            qaPaths = list(set(qaPaths))
            total = len(qaPaths)
            textarea.insert(tk.END, f"QA : {total}\n")
            textarea.yview(tk.END)
            for i, qaPath in enumerate(qaPaths):
                if cancel_event.is_set():
                    return
                time.sleep(1)
                qaPage = get_page_with_retry(qaPath, options)
                qaSoup = BeautifulSoup(qaPage.content, 'html.parser')
                
                # Extract question and answer from the FAQ page
                qContainer = qaSoup.find(class_='faq_qstCont_ttl')
                aContainer = qaSoup.find(class_='faq_ansCont_txt')
                
                # Store question and answer text if found
                questions.append(qContainer.text.strip().replace('\n', '').replace('\r', '') if qContainer else '')
                answers.append(aContainer.text.strip().replace('\n', '').replace('\r', '') if aContainer else '')
                
                # Update progress
                progress = int((i + 1) / total * 100)
                
                # Clear previous text and update processing status
                textarea.delete('1.0', tk.END)  # Clear the entire text area
                textarea.insert(tk.END, f"処理中 {progress}%\n")  # Insert updated text
                textarea.yview(tk.END)
        else:
            # If no QA paths, fall back to the homepage to extract questions and answers
            qContainers = soup.find_all(class_='faq_qstCont_ttl')
            aContainers = soup.find_all(class_='faq_ansCont_txt')
            
            if len(qContainers) != len(aContainers):
                textarea.insert(tk.END, "質問数と回答数の不一致")
                textarea.yview(tk.END)
            else:
                # Loop through and align questions with answers
                for qContainer, aContainer in zip(qContainers, aContainers):
                    questions.append(qContainer.text.strip().replace('\n', '').replace('\r', '') if qContainer else '')
                    answers.append(aContainer.text.strip().replace('\n', '').replace('\r', '') if aContainer else '')

        # Save the data
        df = pd.DataFrame({'Q': questions, 'A': answers})
        df.to_excel('qa.xlsx', index=False, sheet_name='FAQ_データ')

        textarea.insert(tk.END, "終了\n")
        textarea.yview(tk.END)
    except Exception as e:
        textarea.insert(tk.END, f"エラーが発生しました: {str(e)}\n")
        textarea.yview(tk.END)

def on_start_button_click(entry, textarea, cancel_event):
    url = entry.get()
    if not url:
        messagebox.showwarning("入力エラー", "URLを入力してください。")
        return
    # Run the scraping process in a separate thread to avoid freezing the GUI
    threading.Thread(target=scrape_website, args=(url, textarea, cancel_event), daemon=True).start()

def on_cancel_button_click(cancel_event, window):
    cancel_event.set()
    window.quit()

def create_gui():
    window = tk.Tk()
    window.title("FAQ スクラッパー")
    window.iconbitmap('path_to_icon.ico')
    window.geometry("500x300")  # Increased window size for more room
    window.configure(padx=30, pady=10)
    
    # Title Label
    title_label = tk.Label(window, text="FAQ スクラッパー", font=("Noto Sans JP", 18), anchor="center")
    title_label.pack(fill="x", pady=10)

    # Next Website title and input box in one line, full width
    input_frame = tk.Frame(window)
    input_frame.pack(fill="x", pady=10)

    url_label = tk.Label(input_frame, text="URLを入力 : ", font=("Noto Sans JP", 12))
    url_label.pack(side="left", padx=0)
    
    url_entry = tk.Entry(input_frame, width=50, font=("Noto Sans JP", 12))
    url_entry.pack(side="left", fill="x", padx=5)

    # Textarea for logs (4 rows)
    textarea = tk.Text(window, height=5, width=70)  # Set height to 4 rows
    textarea.pack(pady=10)  # Added padding for spacing

    # Start and Cancel buttons with 50% width and height of 40px
    cancel_event = threading.Event()
    
    button_frame = tk.Frame(window)
    button_frame.pack(fill="x", pady=10)

    start_button = tk.Button(button_frame, text="開始", command=lambda: on_start_button_click(url_entry, textarea, cancel_event), height=2, width=30)
    start_button.pack(side="left", fill="x", padx=5)

    cancel_button = tk.Button(button_frame, text="キャンセル", command=lambda: on_cancel_button_click(cancel_event, window), height=2, width=30)
    cancel_button.pack(side="right", fill="x", padx=5)

    window.mainloop()

if __name__ == "__main__":
    create_gui()
