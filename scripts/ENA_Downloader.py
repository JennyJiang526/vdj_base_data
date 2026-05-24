import os
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
import json
import csv


class ENA_Downloader():
    """
    Downloads FASTQ (or submitted) files from ENA for a given project.

    Reads the AIRR metadata.json that was already placed at
    {projects_path}/{project_id}/project_metadata/metadata.json
    to determine which ENA run accessions map to which subject/sample/repertoire,
    then downloads the corresponding FASTQ files into
    {projects_path}/{project_id}/raw_seq/{subject}/{sample}/{repertoire}/.

    Args:
        project_id:    ENA/SRA project accession (e.g. PRJNA349143).
        is_submitted:  If True, download the original submitted files instead of
                       ENA-processed FASTQ files.
        projects_path: Root directory where project folders live.
                       Defaults to the PROJECTS_PATH environment variable.
    """

    def __init__(self, project_id, is_submitted, projects_path=None):
        if projects_path is None:
            projects_path = os.environ.get("PROJECTS_PATH")
        if not projects_path:
            raise ValueError(
                "projects_path must be supplied or set via the PROJECTS_PATH env var"
            )
        self.projects_path = projects_path
        self.download_link = ""
        self.project_id = project_id
        self.repertoires_links = []
        self.repertoires_metadata = {}
        self.is_submitted = is_submitted

    def find_link(self):
        base_url = "https://www.ebi.ac.uk/ena/browser/api/xml/"
        project_url = urljoin(base_url, self.project_id)
        response = requests.get(project_url)
        root = ET.fromstring(response.content)

        project_links = root.find('.//PROJECT_LINKS')
        if project_links is not None:
            for project_link in project_links.findall('.//PROJECT_LINK'):
                xref_link = project_link.find('.//XREF_LINK')
                files = 'ENA-SUBMITTED-FILES' if self.is_submitted else 'ENA-FASTQ-FILES'
                if xref_link is not None and xref_link.find('DB').text in [files]:
                    self.download_link = xref_link.find('ID').text

    
    def download_file(self, url, path):
        response = requests.get(url, stream=True)
        with open(path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)

    def open_metadata(self):
        metadata_path = self.check_metadata_exists()
        with open(metadata_path, 'r') as metadata_file:
            data = json.load(metadata_file)
            for repetoire in data['Repertoire']:
                subject_id = repetoire.get('subject').get('subject_id')
                sample_id = repetoire.get('sample')[0].get('sample_id')
                repertoire_id = repetoire.get('repertoire_id')
                ena_file_name = repetoire.get('sample')[0].get('sequencing_files').get('filename')
                self.repertoires_metadata[ena_file_name] = [subject_id,sample_id,repertoire_id]
        
        
    
    def check_metadata_exists(self):
        project_path = os.path.join(self.projects_path, self.project_id)
        if not os.path.exists(project_path):
            raise Exception(f"{project_path} not exitst")
        
        metadata_path = os.path.join(project_path, "project_metadata", "metadata.json")
        if not os. path.exists(metadata_path):
            raise Exception(f"metadata not found in {metadata_path}")
        
        return metadata_path

    def download_repertoires(self):
        response = requests.get(self.download_link)
        reader = csv.DictReader(response.text.splitlines(), delimiter='\t')

        for row in reader:
            run_accession = row['run_accession']
            if not self.is_submitted:
                fastq_files = row['fastq_ftp'].split(';')
            else:
                fastq_files = row['submitted_ftp'].split(';')
            if run_accession in self.repertoires_metadata:
                file = self.repertoires_metadata[run_accession]
                download_dir = os.path.join(self.projects_path, self.project_id, 'raw_seq', file[0], file[1], file[2])
                os.makedirs(download_dir, exist_ok=True)

                for file_url in fastq_files:
                    if not self.is_submitted:
                        file_name = file_url.split('/')[-1]
                    else:
                        if '_R1.fastq.gz' in file_url:
                            file_name = run_accession + '_1.fastq.gz'
                        else:
                            file_name = run_accession + '_2.fastq.gz'

                    file_path = os.path.join(download_dir, file_name)
                    if not os.path.exists(file_path):
                        self.download_file("https://" + file_url, file_path)
                        print(f"Downloaded {file_name} to {file_path}")

    def start_downloading(self):
        try:
            self.open_metadata()
            self.find_link()
            self.download_repertoires()
        
        except Exception as e:
            print(e)
