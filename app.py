from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from PIL import Image

import pytesseract
import time
import base64
import io
import os
import requests
import random


def read_proxy_list(file_path):
    proxies = []
    with open(file_path, "r") as file:
        for line in file:
            proxies.append(line.strip())
    return proxies


def scrape_web(year, district, taluka, village, article, free_text, output_file):
    output_dir = "downloaded_html"
    os.makedirs(output_dir, exist_ok=True)
    driver = webdriver.Chrome()

    url = "https://pay2igr.igrmaharashtra.gov.in/eDisplay/"
    driver.get(url)

    try:

        def select_dropdown_by_id(id, text):
            dropdown = WebDriverWait(driver, 100).until(
                EC.presence_of_element_located((By.ID, id))
            )
            select = Select(dropdown)
            select.select_by_visible_text(text)
            time.sleep(1)

        def write_input_by_id(id, text, submit=False):
            input_field = WebDriverWait(driver, 100).until(
                EC.presence_of_element_located((By.ID, id))
            )
            input_field.clear()
            input_field.send_keys(text)
            if submit:
                input_field.submit()
                time.sleep(5)
            time.sleep(1)

        def solve_captcha():
            canvas = WebDriverWait(driver, 100).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#captcha canvas"))
            )
            canvas_base64 = driver.execute_script(
                "return arguments[0].toDataURL('image/png').substring(22);", canvas
            )

            image_data = base64.b64decode(canvas_base64)
            image = Image.open(io.BytesIO(image_data))
            image.save("captcha.png")

            captcha_text = pytesseract.image_to_string(image, config="--psm 8")
            return captcha_text.strip()

        def select_all_in_dropdown():
            dropdown = WebDriverWait(driver, 100).until(
                EC.presence_of_element_located((By.ID, "dt-length-0"))
            )
            select = Select(dropdown)
            select.select_by_value("-1")  # Select the option with value "-1" (All)
            time.sleep(2)  # Allow time for the table to update

        # Perform dropdown selections and input text
        select_dropdown_by_id("dbselect", year)
        select_dropdown_by_id("district_id", district)
        select_dropdown_by_id("taluka_id", taluka)
        select_dropdown_by_id("village_id", village)
        select_dropdown_by_id("article_id", article)
        write_input_by_id("free_text", free_text)

        # Solve the captcha
        captcha_text = solve_captcha()
        write_input_by_id("cpatchaTextBox", captcha_text, submit=True)

        # Select "All" in the dropdown
        select_all_in_dropdown()

        # Extract table data
        table = WebDriverWait(driver, 100).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#tableparty tbody"))
        )

        rows = table.find_elements(By.TAG_NAME, "tr")
        links = []

        for index, row in enumerate(rows, start=1):
            try:
                doc_num = row.find_element(By.XPATH, ".//td[1]").text
                sro_code = row.find_element(By.XPATH, ".//td[2]").text
                year = "2023"
                link_element = row.find_element(By.XPATH, ".//td[last()]/a")
                full_link = link_element.get_attribute("href")

                metadata = f"{doc_num},{sro_code},{year},{full_link}"
                links.append(metadata)

            except Exception as e:
                print(f"Row {index}: Error processing row. {e}")

        # Save all links to a file
        with open(output_file, "w", encoding="utf-8") as file:
            for link in links:
                file.write(link + "\n")

        print(f"All links have been saved to '{output_file}'.")

    except Exception as e:
        print(e)

    finally:
        time.sleep(5)
        driver.quit()


# scrape_web(
#     year="2023",
#     district="पुणे",
#     taluka="हवेली",
#     village="वाकड",
#     article="करारनामा",
#     free_text="2023",
#     output_file="links.txt",
# )


def download_with_proxy(url, file_name, proxies):
    for attempt in range(len(proxies)):
        proxy = random.choice(proxies)
        print(f"Attempting with proxy: {proxy}")

        worked = download_pdf(url, file_name, proxy)
        if worked:
            return

    print("All proxies failed for this URL.")


def download_pdf(url, file_name, proxy):
    try:
        response = requests.get(url, stream=True, verify=False, proxies={"http": proxy})
        response.raise_for_status()  # Check for request errors

        with open(file_name, "wb") as file_name:
            for chunk in response.iter_content(chunk_size=8192):
                file_name.write(chunk)

        print(f"PDF downloaded successfully as {file_name}")
        return True
    except Exception as e:
        print(f"Error downloading the PDF: {e}")
        time.sleep(2)
        return False


def read_txt_and_download(proxies):
    with open("temp.txt", "r", encoding="utf-8") as file:
        for line in file:
            doc_no, sro_code, year, url = line.strip().split(
                ",",
            )
            download_with_proxy(url, f"pdfs/{doc_no}_{sro_code}_{year}.pdf", proxies)

    print("All PDFs have been downloaded.")


proxies = read_proxy_list("http_proxies.txt")

read_txt_and_download(proxies)
