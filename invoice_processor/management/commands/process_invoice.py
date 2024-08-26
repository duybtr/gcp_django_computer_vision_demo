from django.core.management.base import BaseCommand
from google.cloud import vision
from google.cloud import storage
import json
import re

def async_detect_document(gcs_source_uri, gcs_destination_uri):
    """OCR with PDF/TIFF as source files on GCS"""
    
    # Supported mime_types are: 'application/pdf' and 'image/tiff'
    mime_type = "application/pdf"

    # How many pages should be grouped into each json output file.
    batch_size = 2

    client = vision.ImageAnnotatorClient()

    feature = vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)

    gcs_source = vision.GcsSource(uri=gcs_source_uri)
    input_config = vision.InputConfig(gcs_source=gcs_source, mime_type=mime_type)

    gcs_destination = vision.GcsDestination(uri=gcs_destination_uri)
    output_config = vision.OutputConfig(
        gcs_destination=gcs_destination, batch_size=batch_size
    )

    async_request = vision.AsyncAnnotateFileRequest(
        features=[feature], input_config=input_config, output_config=output_config
    )

    operation = client.async_batch_annotate_files(requests=[async_request])

    print("Waiting for the operation to finish.")
    operation.result(timeout=420)

    # Once the request has completed and the output has been
    # written to GCS, we can list all the output files.
    storage_client = storage.Client()

    match = re.match(r"gs://([^/]+)/(.+)", gcs_destination_uri)
    bucket_name = match.group(1)
    prefix = match.group(2)

    bucket = storage_client.get_bucket(bucket_name)
    
    # List objects with the given prefix, filtering out folders.
    blob_list = [
        blob
        for blob in list(bucket.list_blobs(prefix=prefix))
        if not blob.name.endswith("/")
    ]
    print("Output files:")
    for blob in blob_list:
        print(blob.name)

    # Process the first output file from GCS.
    # Since we specified batch_size=2, the first response contains
    # the first two pages of the input file.
    output = blob_list[0]

    json_string = output.download_as_bytes().decode("utf-8")
    response = json.loads(json_string)

    return response

from invoice_processor.models import Expense
from datetime import date

class Command(BaseCommand):
    def handle(self, *args, **options):
        client = storage.Client()
        gcs_destination_uri = 'gs://invoices_5236/output/'
        for b in client.list_blobs('invoices_5236', prefix="invoices"):
            if not b.name.endswith("/"):
                gcs_source_uri = f'gs://invoices_5236/{b.name}'
                response = async_detect_document(gcs_source_uri, gcs_destination_uri)
                first_page_response = response["responses"][0]
                annotation = first_page_response["fullTextAnnotation"]         
                raw_text = annotation["text"]
                invoice_number = re.search("Invoice #: (\d{10,15})", raw_text).group(1)
                account_number = re.search("\d{2}\s\d{3}\s\d{3}-\d{1}", raw_text).group(0)
                customer_name = re.search("Customer\sName:\s+([\w\s]+)\\n", raw_text).group(1)
                invoice_amount = re.search("(\\n[-\$]*\d+\.\d{0,2}){5}", raw_text).group(1).replace('\n$','').strip().replace("$","")
                invoice_date = re.search("Bill Date:\s+(\d{1,2}\/\d{1,2}\/\d{4})", raw_text).group(1)
                month, day, year = invoice_date.split("/")
                expense = Expense.objects.create(
                    invoice_number = invoice_number,
                    account_number = account_number,
                    customer_name = customer_name,
                    invoice_amount = invoice_amount,
                    invoice_date = date(int(year), int(month), int(day))
                )
                print(f"Expense {expense.id} created")