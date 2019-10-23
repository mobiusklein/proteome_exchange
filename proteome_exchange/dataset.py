import os
import logging

try:
    from urllib2 import urlopen
    from urllib2 import URLError
except ImportError:
    from urllib.request import urlopen
    from urllib.error import URLError

from collections import namedtuple
from lxml import etree

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty

import threading

from .utils import Base, Bundle


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


DatasetIdentifier = namedtuple("DatasetIdentifier", ['repository', 'id'])


class Contact(Bundle):
    pass


class Species(Bundle):
    pass


class Dataset(Base):
    def __init__(self, id, summary, species=None, instruments=None, contacts=None, dataset_files=None):
        self.id = id
        self.summary = summary
        self.species = species
        self.instruments = instruments
        self.contacts = contacts
        self.dataset_files = dataset_files

    def __iter__(self):
        return iter(self.dataset_files)

    def __getitem__(self, i):
        return self.dataset_files[i]

    def __len__(self):
        return len(self.dataset_files)

    def download(self, destination=None, filter=None, threads=None):
        if threads is None:
            threads = 0
        if destination is None:
            destination = '.'
        if threads == 1:
            for data_file in self:
                if filter is not None and filter(data_file):
                    continue
                logger.info(
                    "Downloading %s to %s",
                    data_file.name,
                    os.path.join(destination, data_file.name))
                data_file.download(
                    os.path.join(destination, data_file.name))
        else:
            inqueue = Queue()
            for data_file in self:
                if filter is not None and filter(data_file):
                    continue
                inqueue.put((data_file, os.path.join(destination, data_file.name)))

            def _work():
                while 1:
                    try:
                        data_file, destination = inqueue.get(False, 3.0)
                        logger.info("Downloading %s to %s", data_file.name, destination)
                        try:
                            data_file.download(destination)
                        except URLError as err:
                            logger.error("An error occurred, retrying", exc_info=True)
                            import time
                            time.sleep(2)
                            data_file.download(destination)
                    except Empty:
                        break

            if threads <= 0:
                threads = len(self)
            workers = []
            for i in range(threads):
                worker = threading.Thread(target=_work)
                worker.start()
                workers.append(worker)

            for worker in workers:
                worker.join()

    @staticmethod
    def parse_identifier_list(node):
        return [DatasetIdentifier(x[0].attrib['name'], x[0].attrib['value']) for x in node.findall(".//DatasetIdentifier")]

    @staticmethod
    def parse_species_list(node):
        species = []
        for spec in node.findall(".//Species"):
            entry = Species()
            for param in spec:
                param = param.attrib
                entry[param['name'].replace("taxonomy: ", "")] = param['value']
            species.append(entry)
        return species

    @staticmethod
    def parse_instrument_list(node):
        instruments = []
        for inst in node.findall(".//Instrument"):
            entry = {}
            entry['id'] = inst.attrib['id']
            for param in (p.attrib for p in inst):
                entry[param['name']] = param.get('value', True)
            instruments.append(entry)
        return instruments

    @staticmethod
    def parse_contacts_list(node):
        contacts = []
        for contact in node.findall(".//Contact"):
            entry = Contact()
            for param in (p.attrib for p in contact):
                entry[param['name']] = param.get('value', True)
            contacts.append(entry)
        return contacts

    @classmethod
    def from_xml(cls, node):
        return cls(
            id=node.attrib['id'],
            summary=DatasetSummary.from_xml(node.find("./DatasetSummary")),
            species=cls.parse_species_list(node),
            instruments=cls.parse_instrument_list(node),
            contacts=cls.parse_contacts_list(node),
            dataset_files=[DatasetFile.from_xml(
                n) for n in node.findall(".//DatasetFile")],
        )

    @classmethod
    def get(cls, accession):
        url = "http://proteomecentral.proteomexchange.org/cgi/GetDataset?ID={accession}&outputMode=XML&test=no"
        url = url.format(accession=accession)
        fd = urlopen(url)
        return cls.from_xml(etree.parse(fd).getroot())


get = Dataset.get


class DatasetSummary(Base):
    def __init__(self, title, hosting_repository, description, review_level, repository_support):
        self.title = title
        self.hosting_repository = hosting_repository
        self.description = description
        self.review_level = review_level
        self.repository_support = repository_support

    @classmethod
    def from_xml(cls, node):
        return cls(
            title=node.attrib['title'],
            hosting_repository=node.attrib['hostingRepository'],
            description=node.find("Description").text,
            review_level=node.find("ReviewLevel")[0].attrib['name'],
            repository_support=node.find("RepositorySupport")[
                0].attrib['name'],
        )


class DatasetFile(Base):
    MAX_LEN_DISPLAY = 256

    def __init__(self, id, name, file_type, uri):
        self.id = id
        self.name = name
        self.file_type = file_type
        self.uri = uri

    @classmethod
    def from_xml(cls, node):
        return cls(
            node.attrib['id'],
            node.attrib['name'],
            node.find(".//cvParam").attrib['name'].replace("URI", "").strip(),
            node.find(".//cvParam").attrib['value']
        )

    def download(self, destination=None):
        if destination is None:
            destination = self.name
        if not hasattr(destination, 'write'):
            fh = open(destination, 'wb')
        else:
            fh = destination
        source = urlopen(self.uri)
        with fh:
            chunk_size = 2 ** 16
            chunk = source.read(chunk_size)
            while chunk:
                fh.write(chunk)
                chunk = source.read(chunk_size)
