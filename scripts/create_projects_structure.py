import os
import shutil
import json
import unicodedata
import re
import time
from json_to_tsv import create_tsv_files
from extract_sequences_from_ADC_annotations import start_extraction

def slugify(value, allow_unicode=False):
    # Converts a string into a slug format, which is easier to handle in file systems
    value = str(value)
    if allow_unicode:
        # Normalize unicode characters if allowed
        value = unicodedata.normalize("NFKC", value)
    else:
        # Convert to ASCII and ignore non-ASCII characters
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    # Remove any character that is not a word character or hyphen
    value = re.sub(r"[^\w\s-]", "", value)
    # Replace repeated hyphens with a single hyphen
    return re.sub(r"[-]+", "-", value).strip("-_")

def create_new_structure(project, projects_path):
    # Creates a new directory structure for a specific project
    project_path = os.path.join(projects_path, project)
    metadata_file = os.path.join(project_path, "metadata.json")
    
    with open(metadata_file, 'r') as metadata_file:
        metadata = json.load(metadata_file)
        # Create a folder for raw sequence data
        adc_annotated_folder_path = os.path.join(project_path, "adc_annotated")
        if not os.path.isdir(adc_annotated_folder_path):
            os.mkdir(adc_annotated_folder_path)

            # Organize data by subject and sample ID
            for repertoire in metadata["Repertoire"]:
                subject_id = slugify(repertoire["subject"]["subject_id"])
                subject_id_folder_path = os.path.join(adc_annotated_folder_path, subject_id)
                if not os.path.isdir(subject_id_folder_path):
                    os.mkdir(subject_id_folder_path)
                
                for sample in repertoire["sample"]:
                    sample_id = slugify(sample["sample_id"])
                    sample_id_folder_path = os.path.join(subject_id_folder_path, sample_id)
                    if not os.path.isdir(sample_id_folder_path):
                        os.mkdir(sample_id_folder_path)

                # Move repertoire files to the corresponding run folder, matching the
                # subject/sample/run layout used by the ENA FASTQ download (raw_seq/)
                run_accession = slugify(get_run_accession(repertoire))
                repertoire_folder_path = os.path.join(sample_id_folder_path, run_accession)
                if not os.path.isdir(repertoire_folder_path):
                    os.mkdir(repertoire_folder_path)
                repertoire_path = os.path.join(project_path, repertoire["repertoire_id"] + ".tsv.gz")
                create_ids_json(repertoire["repertoire_id"], subject_id, sample_id, run_accession, repertoire_folder_path)
                shutil.move(repertoire_path, repertoire_folder_path)


def get_run_accession(repertoire):
    # Same field ENA_Downloader.py uses to match AIRR metadata against ENA run accessions.
    # Falls back to repertoire_id for repositories that don't populate sequencing_files.
    sequencing_files = repertoire["sample"][0].get("sequencing_files") or {}
    return sequencing_files.get("filename") or repertoire["repertoire_id"]


def create_ids_json(repertoire_id, subject_id, sample_id, run_accession, repertoire_folder_path):
    # Named per repertoire_id since multiple repertoires (e.g. heavy/light chain)
    # can share the same run folder
    json_path = os.path.join(repertoire_folder_path, f'{repertoire_id}.json')
    # Create a dictionary with the provided data
    data = {
        "repertoire_id": repertoire_id,
        "subject_id": subject_id,
        "sample_id": sample_id,
        "run_accession": run_accession
    }

    # Write the dictionary to a JSON file at the specified path
    with open(json_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)
    


def move_metadata_file(project, projects_path):
    # Moves the metadata file of a project to a specific folder
    project_path = os.path.join(projects_path, project)
    metadata_file_path = os.path.join(project_path, "metadata.json")
    remove_unicode_from_metadata(metadata_file_path)
    metadata_folder = os.path.join(project_path, "project_metadata")

    if not os.path.isdir(metadata_folder):
        os.mkdir(metadata_folder)
    
    shutil.move(metadata_file_path, metadata_folder)

def remove_unicode_from_metadata(file_path):
    # Removes non-ASCII characters from metadata files
    with open(file_path, 'r', encoding='utf-8') as file:
        data = file.read()
    cleaned_data = re.sub(r'[^\x00-\x7F]+', '', data)
    data_dict = json.loads(cleaned_data)
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data_dict, file, ensure_ascii=False, indent=4)

def start_new_structure(project_name, projects_path):
    # Initiates the process of creating a new project structure
    print(f"creating new structure for {project_name}")
    create_new_structure(project_name, projects_path)
    move_metadata_file(project_name, projects_path)
    print(f"finished creating new structure for {project_name}")
    time.sleep(2)
    print(f"start to exctract sequences from {project_name}")
    start_extraction(project_name, projects_path)



