import argparse
import os
import shutil

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext


def crawl_downloads(page: Page, context: BrowserContext, cwd: str):
    page.wait_for_selector('xpath=//*[@id="onetidDoclibViewTbl0"]')
    room_id = page.url.split('/')[4]

    # link list
    files = page.query_selector_all(
        'xpath=//tbody/tr/td/div/a[@class="ms-listlink ms-draggable"]')
    folders = page.query_selector_all(
        'xpath=//tbody/tr/td/div/a[@class="ms-listlink"]/parent::div/parent::td/parent::tr')

    for folder in folders:

        href = folder.query_selector(
            'xpath=/td/div/a[@class=\"ms-listlink\"]').get_attribute('href')
        folder_url = f"https://osca.hs-osnabrueck.de{href}"
        folder_name = folder.query_selector(
            "xpath=/td[3]/div/a").text_content().replace(":", "-").strip()+"/"
        new_tab = context.new_page()

        while True:
            try:
                new_tab.goto(folder_url, wait_until="domcontentloaded")
                break
            except:
                print(f"[RETRY]  {cwd+folder_name}")
        crawl_downloads(new_tab, context, cwd+folder_name)
        new_tab.close()

    for file in files:
        file_url = file.get_attribute('href')
        file_name = file_url.split('/')[-1].strip()

        file_download_link = f"https://osca.hs-osnabrueck.de/lms/{room_id}/_layouts/15/download.aspx?SourceUrl={file_url}".replace(
            '+', '%2B')
        while True:
            try:
                with page.expect_download() as download_info:
                    page.goto(file_download_link)
                download = download_info.value
                path = download.path()
                break
            except Exception as ex:
                print(f"[RETRY]  {cwd+file_name}")

        os.makedirs(os.path.dirname(cwd), exist_ok=True)
        shutil.move(path, cwd+file_name)

        print(f"[SUCCESS] {cwd+file_name}")


def run(user, password, path):
    with sync_playwright() as playwright:
        browser: Browser = playwright.firefox.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        page.goto("https://osca.hs-osnabrueck.de")

        page.fill('input[id=Ecom_User_ID]', user)
        page.fill('input[id=Ecom_Password]', password)
        with page.expect_navigation():
            page.click("span[id=loginButton2]")

        page.click('a[id=owncss_BenutzerMenue_Links_102]')
        page.click("div[id=div_SelectedSemester]")
        page.click("#div_semesterchoise_selectbox > div:nth-child(1)")

        rooms = page.query_selector_all("a[class=owncss_teamraeume_link]")

        for room in rooms:
            with page.expect_popup() as popup_info:
                room.click()
            room_page = popup_info.value
            # goto files
            room_page.click("div[id=sitenavigationelement_2]")
            room_name = room.text_content().replace(':', '').replace('/', '-').strip()

            crawl_downloads(room_page, context,
                            f"{path}/{room_name}/")

            room_page.close()
        context.close()
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Crawler that downloads all files from your OSCA courses')

    parser.add_argument('-d', '--path',
                        dest='path',
                        help='Path for files',
                        required=False,
                        default='./download')
    parser.add_argument('-u', '--user',
                        dest='user',
                        help='username',
                        required=True)
    parser.add_argument('-p', '--password',
                        dest='password',
                        help='password',
                        required=True)

    arg = vars(parser.parse_args())
    run(arg['user'], arg['password'], arg['path'])
