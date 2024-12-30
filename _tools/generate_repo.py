"""
    Repository, addons.xml and addons.xml.md5 structural generator

        Modifications:

        - Zip plugins/repositories to a "zip" folder
        - Create a repository addon, skip folders without addon.xml, user config file
        - Works with Python3

    This file is provided "as is", without any warranty whatsoever. Use at your own risk
"""
import os
import hashlib
import zipfile
import shutil
from xml.dom import minidom
import glob
import datetime
import traceback
import configparser  # Changed from ConfigParser

class Generator:
    """
        Generates a new addons.xml file from each addons addon.xml file
        and a new addons.xml.md5 hash file. Must be run from a subdirectory (eg. _tools) of
        the checked-out repo. Only handles single depth folder structure.
    """

    def __init__(self):
        """
        Load the configuration
        """
        self.config = configparser.ConfigParser()  # Changed from SafeConfigParser
        self.config.read('config.ini')

        self.tools_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__))))
        self.output_path = "_" + self.config.get('locations', 'output_path')

        self.excludes = self.config.get('addon', 'excludes').split(',')

        # travel path one up
        os.chdir(os.path.abspath(os.path.join(self.tools_path, os.pardir)))

        # generate files
        self._pre_run()
        self._generate_repo_files()
        self._generate_addons_file()
        self._generate_md5_file()
        self._generate_zip_files()

        # notify user
        print("Finished updating addons xml, md5 files and zipping addons")
        print("Always double-check your MD5 Hash using a site like http://onlinemd5.com/ if the repo is not showing files or downloading properly.")

    def _pre_run(self):
        # create output path if it does not exist
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)

    def _generate_repo_files(self):
        addonid = self.config.get('addon', 'id')
        name = self.config.get('addon', 'name')
        version = self.config.get('addon', 'version')
        author = self.config.get('addon', 'author')
        summary = self.config.get('addon', 'summary')
        description = self.config.get('addon', 'description')
        url = self.config.get('locations', 'url')

        if os.path.isfile(addonid + os.path.sep + "addon.xml"):
            return

        print("Create repository addon")

        with open(self.tools_path + os.path.sep + "template.xml", "r", encoding="utf-8") as template:
            template_xml = template.read()

        repo_xml = template_xml.format(
            addonid=addonid,
            name=name,
            version=version,
            author=author,
            summary=summary,
            description=description,
            url=url,
            output_path=self.output_path)

        # save file
        if not os.path.exists(addonid):
            os.makedirs(addonid)

        self._save_file(repo_xml, file=addonid + os.path.sep + "addon.xml")

    def _generate_zip_files(self):
        addons = os.listdir(".")
        for addon in addons:
            _path = os.path.join(addon, "addon.xml")
            if not os.path.isfile(_path):
                continue
            try:
                if not os.path.isdir(addon) or addon in [".git", self.output_path, self.tools_path]:
                    continue
                document = minidom.parse(_path)
                for parent in document.getElementsByTagName("addon"):
                    version = parent.getAttribute("version")
                    addonid = parent.getAttribute("id")
                self._generate_zip_file(addon, version, addonid)
            except:
                failure = traceback.format_exc()
                print('Kodi Repo Generator Exception: \n' + str(failure))

    def _generate_zip_file(self, path, version, addonid):
        print("Generate zip file for " + addonid + " " + version)
        filename = path + "-" + version + ".zip"
        try:
            with zipfile.ZipFile(filename, 'w') as zip:
                for root, dirs, files in os.walk(path + os.path.sep):
                    for file in files:
                        ext = os.path.splitext(file)[-1].lower()
                        if ext not in self.excludes:
                            zip.write(os.path.join(root, file))

            if not os.path.exists(self.output_path + addonid):
                os.makedirs(self.output_path + addonid)

            if os.path.isfile(self.output_path + addonid + os.path.sep + filename):
                os.rename(self.output_path + addonid + os.path.sep + filename,
                          self.output_path + addonid + os.path.sep + filename + "." + datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
            shutil.move(filename, self.output_path + addonid + os.path.sep + filename)
            shutil.copy(addonid + '/addon.xml', self.output_path + addonid + os.path.sep + 'addon.xml')
            try:
                shutil.copy(addonid + '/icon.png', self.output_path + addonid + os.path.sep + 'icon.png')
            except:
                print('**** Icon file missing for ' + addonid)
            try:
                shutil.copy(addonid + '/fanart.jpg', self.output_path + addonid + os.path.sep + 'fanart.jpg')
            except:
                print('**** Fanart file missing for ' + addonid)

        except:
            failure = traceback.format_exc()
            print('Kodi Repo Generator Exception: \n' + str(failure))

    def _generate_addons_file(self):
        addons = os.listdir(".")
        addons_xml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<addons>\n"
        for addon in addons:
            _path = os.path.join(addon, "addon.xml")
            if not os.path.isfile(_path):
                continue
            try:
                with open(_path, "r", encoding="utf-8") as f:
                    addon_xml = f.read()
                addons_xml += addon_xml + "\n\n"
            except:
                failure = traceback.format_exc()
                print(f"Excluding {_path} for {addon}")
                print("Exception Details:")
                print(failure)

        addons_xml = addons_xml.strip() + "\n</addons>\n"
        self._save_file(addons_xml, file=self.output_path + "addons.xml")

    def _generate_md5_file(self):
        try:
            hash_object = hashlib.md5()
            with open(self.output_path + 'addons.xml', 'rb') as addons_file:
                hash_object.update(addons_file.read())

            result = hash_object.hexdigest()
            self._save_file(result, file=self.output_path + "addons.xml.md5")
        except:
            failure = traceback.format_exc()
            print("**** An error occurred creating addons.xml.md5 file!\n")
            print('Kodi Repo Generator Exception: \n' + str(failure))

    def _save_file(self, data, file):
        try:
            with open(file, "w", encoding="utf-8") as f:
                f.write(data)
        except:
            failure = traceback.format_exc()
            print(f"**** An error occurred saving {file} file!\n")
            print('Kodi Repo Generator Exception: \n' + str(failure))

if __name__ == "__main__":
    Generator()
