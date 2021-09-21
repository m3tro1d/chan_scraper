import os
import sys
import time

try:
    import requests
except ImportError:
    print("'requests' module is not installed", file=sys.stderr)
    sys.exit(1)

from extractors.dvach import Dvach
from extractors.fourchan import Fourchan


class Scraper:
    """The main scraper class"""
    def __init__(self, urls, mode, output, pause):
        self.urls = urls
        self.mode = mode
        self.output = output
        self.pause = pause

        self.urls_len = len(self.urls)
        self.is_single_mode = self.urls_len == 1

        self.extractors = (
            Dvach,
            Fourchan,
            # Add extractors here
        )

    def scrap(self):
        """Fires the scraping according to the URL amount"""
        if self.is_single_mode:
            self.scrap_thread(self.urls[0])
        else:
            self.scrap_multiple_threads()

    def scrap_thread(self, url):
        """Scraps the thread according to self params and URL"""
        print(f"Scraping '{url}'")
        try:
            extractor = self.select_extractor(url)
            file_list = extractor.get_files_urls_names()
            file_list = self.filter_files(file_list)
            amount = self.get_and_check_amount(file_list)
            thread_dir = self.get_thread_dir(extractor)
            self.download_files(file_list, thread_dir, amount)
        except Exception as error:
            # Intercept thread-level errors
            print(f"Error while parsing {url}: {error}", file=sys.stderr)

    def scrap_multiple_threads(self):
        """Batch scraps the threads according to self params"""
        for i, url in enumerate(self.urls, start=1):
            print(f"\n[{i}/{self.urls_len}]")
            self.scrap_thread(url)

    def select_extractor(self, url):
        """Returns the initialized extractor that matches the specified URL"""
        for ex in self.extractors:
            match = ex.match(url)
            if match:
                return ex(match.group(0))
        raise Exception("URL is not supported")

    def filter_files(self, file_list):
        """Filters the files based on the current mode"""
        filtered = tuple(filter(lambda f: self.is_needed_file(f[1]), file_list))
        return filtered

    def get_and_check_amount(self, file_list):
        """Raises an exception if the list is empty, otherwise returns length"""
        if not file_list:
            raise Exception("There are no files")
        return len(file_list)

    def is_needed_file(self, file_name):
        """Checks if the file is right according to its extension and mode"""
        ext = self.get_extension(file_name)
        return ((self.mode == "images" and self.is_image(ext)) or
                (self.mode == "videos" and self.is_video(ext)) or
                (self.mode == "all"))

    def get_extension(self, file_name):
        """Returns files extension"""
        return file_name.split(".")[-1]

    def is_image(self, ext):
        """Returns true if ext is an image type"""
        return ext in ("jpg", "jpeg", "png", "gif")

    def is_video(self, ext):
        """Returns true if ext is a video type"""
        return ext in ("webm", "mp4")

    def get_thread_dir(self, extractor):
        """Returns the output directory according to the URL amount"""
        thread_dir = self.output
        if not self.is_single_mode:
            thread_dir = self.create_thread_dir(extractor)
        return thread_dir

    def create_thread_dir(self, extractor):
        """Creates and returns the directory for the particular thread"""
        new_dir_name = f"{extractor.name}_{extractor.board_name}_{extractor.thread_number}"
        new_dir = os.path.join(self.output, new_dir_name)
        if not os.path.isdir(new_dir):
            os.mkdir(new_dir)
        return new_dir

    def download_files(self, file_list, thread_dir, amount):
        """Downloads the files with the specified parameters"""
        for i, (file_url, file_name) in enumerate(file_list, start=1):
            file_path = os.path.join(thread_dir, file_name)
            self.handle_and_save(file_url, file_path, i, amount)

    def handle_and_save(self, url, name, i, amount):
        """Handles one file saving iteration"""
        try:
            is_saved = self.save_file(url, name)
            if self.pause and is_saved:
                time.sleep(0.5)
        except Exception as error:
            # Intercept file-level errors and move on
            print(f"{i:>4}/{amount} - ERROR {os.path.basename(name)}: {error}",
                  file=sys.stderr)
        else:
            print(f"{i:>4}/{amount} - {os.path.basename(name)}")

    def save_file(self, url, name):
        """Save the file on the URL; returns True if the file was downloaded"""
        if not os.path.isfile(name):
            with open(name, "wb") as file:
                for chunk in self.request_get(url):
                    file.write(chunk)
            return True
        return False

    def request_get(self, url):
        """Sends a properly structured GET request and returns the response"""
        response = requests.get(url)
        response.raise_for_status()
        return response
