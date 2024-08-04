from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import os
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException
from bs4 import BeautifulSoup
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from mongoengine import connect
from dataclasses import dataclass, asdict
from datetime import date
import datetime
from mongo_patent import MongoPatent
import re
from fake_useragent import UserAgent

@dataclass
class JP_Patent_Data:
    patent_number: str
    pdf_url: list
    priority_date: date
    filing_date: date
    publication_date: date
    abstract: str
    specification: str
    claims: list
    title: str
    jurisdiction: str
    inventors: list
    assignees: list
    status: str
    classifications: str
    images: list

class JP_Patent:
    def __init__(self):
        options = Options()
#        options.headless = True
        driver = webdriver.Chrome(options=options)
        self.driver = driver
        MONGO_URI = "mongodb+srv://dioochei:gvTYA0f7vUD4UWHD@cluster0.xkcjmb4.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        
        PYMONGO_CLIENT = MongoClient(MONGO_URI, server_api=ServerApi('1'))
        connect(host=MONGO_URI)
        try:
            PYMONGO_CLIENT.admin.command("ping")
            print("successfully pinged mongo")
        except Exception as e:
            print(e)
            print("fail")
        time.sleep(1)
        self.visit_site()

    def visit_site(self):
        self.driver.maximize_window()
        self.driver.get('https://www.j-platpat.inpit.go.jp/')
        WebDriverWait(self.driver, 50).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))
        time.sleep(10)
        lang = self.driver.find_element(By.LINK_TEXT, "English")
        self.driver.execute_script('arguments[0].click();', lang)
        self.search_patents()
        return
        
    def search_patents(self):
            start_year = 1976
            start_patent_num = '000001'
            end_patent_num = str(int(start_patent_num) + 99).zfill(len(start_patent_num))
            
            patent = self.driver.find_element(By.XPATH, '//a[contains(@id, "cfc001_globalNav_item_0")]')
            time.sleep(0.5)
            actions = ActionChains(self.driver)
            actions.move_to_element(patent).perform()
            time.sleep(1)
            self.driver.find_element(By.XPATH, '//a[contains(@id, "cfc001_globalNav_sub_item_0_0")]').click()
            WebDriverWait(self.driver, 50).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))
            time.sleep(10)
            self.driver.find_element(By.XPATH, '//input[contains(@id, "p00_rdoDocInputTypeButton_1-input")]').click()
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            start_input_tag = self.driver.find_element(By.XPATH, '//input[contains(@id, "p00_srchCondtn_txtDocNoRangeStartNo")]')
            end_input_tag = self.driver.find_element(By.XPATH, '//input[contains(@id, "p00_srchCondtn_txtDocNoRangeEndNo")]')
            search_btn = self.driver.find_element(By.XPATH, '//a[contains(@id, "p00_searchBtn_btnDocInquiry")]')
            
            while start_year <= datetime.datetime.now().year:
                start_input_tag.clear()
                end_input_tag.clear()
                start_input_tag.send_keys(str(start_year) + '-' + start_patent_num)
                end_input_tag.send_keys(str(start_year) + '-' + end_patent_num)
                search_btn.click()
                WebDriverWait(self.driver, 50).until(EC.presence_of_element_located, ((By.XPATH, '//patentutltyintnlnumonlylst[contains(@class, "ng-star-inserted")]')))
                time.sleep(10)
                self.driver.find_element(By.XPATH, '//p[contains(@id, "patentUtltyIntnlNumOnlyLst_tableView_publicNumArea0")]').click()
                self.extract_patent_data()
                start_patent_num = end_patent_num
                end_patent_num = str(int(end_patent_num) + 99).zfill(len(end_patent_num))
                if(int(start_patent_num[0]) > 0) :
                    start_year = start_year + 1
            
    def extract_patent_data(self):
        index = 0
        pub_num = ''
        self.driver.switch_to.window(self.driver.window_handles[1])
        WebDriverWait(self.driver, 50).until(EC.presence_of_element_located, ((By.CSS_SELECTOR, "body")))
        time.sleep(5)
        
        
        
        while True:
            index = 0
            WebDriverWait(self.driver, 50).until(EC.presence_of_element_located, ((By.CSS_SELECTOR, 'body')))
            time.sleep(10)
            biblio = self.driver.find_elements(By.XPATH, '//div[contains(@class, "wordBreak")]')
            if not biblio:
                try:
                    self.driver.find_element(By.XPATH, '//a[contains(@id, "linkSpread_1")]').click()
                    WebDriverWait(self.driver, 50).until(EC.presence_of_element_located, ((By.XPATH, '//div[contains(@id, "p0201_DocuDispArea_isBiblioAccordionOpened_DocuDispArea_BBL")]')))
                    time.sleep(5)
                except NoSuchElementException:
                    pass
            try:
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                if not biblio:
                    pub_num_div = soup.find('div', class_="B100_B110")
                    pub_num = pub_num_div.find('div', class_="contents_bbl").text.strip()
                else:
                    pub_num_div = soup.find(text=lambda x: x and "Publication number" in x)
                    pub_num = pub_num_div.split()[-1]
                
            except AttributeError:
                pass
            if not os.path.exists('data'):
                os.makedirs('data')
            try:
                if pub_num != '':
                    images = []
                    os.mkdir('data/{0}'.format(pub_num))
                    with open('data/{0}/{1}.html'.format(pub_num, str(index).zfill(20)), 'w') as f:
                        f.write(page_source)
                    if biblio:
                        try:
                            images = self.image_urls(soup)
                        except AttributeError:
                            images = []
                    pdf_urls = self.get_pdf_urls()
                    self.driver.find_element(By.XPATH, '//input[contains(@id, "rdoTxtPdfView_0-input")]').click()
                    patent_element = self.patent_from_local(pub_num)
                    result_patent =  JP_Patent_Data(
                        patent_number = patent_element['pub_num'],
                        pdf_url = pdf_urls,
                        priority_date = date(1,1,1),
                        filing_date = patent_element['filing_date'],
                        publication_date = patent_element['pub_date'],
                        abstract = patent_element['abstract'],
                        specification = '',
                        claims = [],
                        title = patent_element['title'],
                        jurisdiction = "Japan",
                        inventors = patent_element['inventors'],
                        assignees = [],
                        status = '',
                        classifications = '',
                        images = images,
                    )
                    self.save_patent_to_db(result_patent)
                
                try:
                    next_btn = self.driver.find_element(By.XPATH , '//a[contains(@id, "cfc003_main_lblNext")]')
                    next_btn.click()
                except NoSuchElementException:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    return
                except ElementClickInterceptedException:
                    pass
                    
            except FileExistsError:
                try:
                    next_btn = self.driver.find_element(By.XPATH , '//a[contains(@id, "cfc003_main_lblNext")]')
                    next_btn.click()
                except NoSuchElementException:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    return
        
 
            
        
        

    def patent_from_local(self, pub_num):
        patent_value = {}
        with open('data/{0}/00000000000000000000.html'.format(pub_num)) as f:
            page = '\n'.join(f.readlines())
            soup = BeautifulSoup(page, 'html.parser')
            try:
                pub_num_div = soup.find('div', class_="B100_B110")
                pub_num = pub_num_div.find('div', class_="contents_bbl").text.strip()
            except AttributeError:
                pub_num_div = soup.find(text=lambda x: x and "Publication number" in x)
                pub_num = pub_num_div.split()[-1]
            
            try:
                filing_div = soup.find('div', class_="B200_B220")
                filing_date = filing_div.find('div', class_="contents_bbl").text.strip()
                parse_filing_date = datetime.datetime.strptime(filing_date, "%b.%d,%Y").strftime("%Y-%m-%d")
            except AttributeError:
                filing_div = soup.find(text=lambda x: x and "Filing date" in x)
                filing_date = filing_div.split()[-1]
                parse_filing_date = datetime.datetime.strptime(filing_date, "%Y%m%d").strftime("%Y-%m-%d")
            
            try:
                pub_div = soup.find('div', class_="B100_B140")
                pub_date = pub_div.find('div', class_="contents_bbl").text.strip()
                parse_pub_date = datetime.datetime.strptime(pub_date, "%b.%d,%Y").strftime("%Y-%m-%d")
            except AttributeError:
                pub_div = soup.find(text=lambda x: x and "Date of publication of application" in x)
                pub_date = pub_div.split()[-1]
                parse_pub_date = datetime.datetime.strptime(pub_date, "%Y%m%d").strftime("%Y-%m-%d")
                
            try:
                abstract = soup.find('div', class_="abstract_p")
                ab_content = abstract.find('div', class_="contents").text.strip()
            except AttributeError:
                ab_content = ""
                for element in soup.find_all(string=True):
                    if "SOLUTION:" in element:
                        ab_content = element.split("SOLUTION:")[1].strip()
                        break
            
            try:
                title_div = soup.find('div', class_="B540_B542")
                title = title_div.find('div', class_="contents_bbl").text.strip()
            except AttributeError:
                title_div = soup.find(text=lambda x: x and "Title of the invention" in x)
                title = title_div.split()[-1]
            
            try:
                inventor_div = soup.find('div', class_="B720_B721")
                inventors = inventor_div.find('div', class_="contents_bbl").get_text(separator='\n').split('\n')
            except AttributeError:
                inventors = []
                for element in soup.find_all(text=lambda x: x and "Full name" in x):
                    inventors.append(element.split()[-1])
            
            patent_value['pub_num'] = pub_num
            patent_value['filing_date'] = parse_filing_date
            patent_value['pub_date'] = parse_pub_date
            patent_value['abstract'] = ab_content
            patent_value['title'] = title
            patent_value['inventors'] = inventors
            
            return patent_value
            
    def image_urls(self, soup):
        img_urls = []
        while True:
            img_div = soup.find('div', class_="image-area-disp_height")
            img_url = img_div.find('img', class_="main_image").get('src')
            img_urls.append(img_url)
            try:
                next_btn = self.driver.find_element(By.XPATH, '//a[contains(@id, "pagerNext")]')
                next_btn.click()
                time.sleep(5)
            except ElementNotInteractableException:
                break
        return img_urls
                
    def save_patent_to_db(self, res_patent):
          if res_patent.patent_number:
              existing_patent = MongoPatent.objects(patent_number=res_patent.patent_number).first()
              if existing_patent:
                  print(res_patent.patent_number, "is already exist on database!")
                  return
              else:
                  patent = MongoPatent(**asdict(res_patent))
                  patent.save()
                  print(res_patent.patent_number, "saved on database successfully!")
          return

    def get_pdf_urls(self):
        pdf_urls = []
        self.driver.find_element_by_xpath("//mat-radio-button[contains(@id, 'rdoTxtPdfView_1')]").click()
        WebDriverWait(self.driver, 50).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'section[id*="pdfArea"]')))
        time.sleep(5)
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        while True:
            time.sleep(5)
            embed_tag = soup.find('embed', id=re.compile('p0201_pdfObj'))
            if embed_tag:
                url = embed_tag.get('src')
                pdf_urls.append(url)
            try:
                next_button = self.driver.find_element(By.XPATH, "//a[contains(@id, 'p02_main_lblNext')]")
                next_button.click()
            except NoSuchElementException:
                break
            except ElementClickInterceptedException:
                pass
        
        return pdf_urls
        
JP_Crawler = JP_Patent()
