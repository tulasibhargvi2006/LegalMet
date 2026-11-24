import cv2
import re
import numpy as np
import easyocr

class OCREngine:
    def __init__(self):
        # Initialize EasyOCR reader for English
        self.reader = easyocr.Reader(['en'])

    def extract_text(self, image_path):
        """
        Use EasyOCR to extract text from the image.
        Returns raw text as a single string with newlines.
        """
        results = self.reader.readtext(image_path, detail=0, paragraph=False)
        # results is a list of strings, each string is a line of recognized text
        text = '\n'.join(results)
        return text

    def extract_fields(self, text):
        """
        Parse the raw OCR text to extract key fields using regex patterns.
        """
        fields = {}

        # ---------- MRP / Price ----------
        mrp_patterns = [
            r'(?:mrp|price|rs\.?)\s*[:?]?\s*[:]?\s*[₹₹]?\s*(\d+\.?\d*)\s*(\d+\.?\d*)?',
            r'₹\s*(\d+\.?\d*)',
            r'rs\.?\s*(\d+\.?\d*)',
            r'price\s*[:?]?\s*[:]?\s*[₹₹]?\s*(\d+\.?\d*)\s*(\d+\.?\d*)?',
        ]
        for pat in mrp_patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                try:
                    if match.group(2) is not None:
                        mrp_val = match.group(1) + '.' + match.group(2)
                    else:
                        mrp_val = match.group(1)
                except IndexError:
                    mrp_val = match.group(1)
                fields['mrp'] = '₹' + mrp_val
                break

        # ---------- Net Quantity ----------
        net_patterns = [
            r'(?:net\s*(?:weight|content|qty|quantity)|weight|qty|quantity)\s*[:]?\s*(\d+\.?\d*)\s*(g|kg|ml|l|gm|kgs)',
            r'net\s*weight\s*[:]?\s*(\d+\.?\d*)\s*(g|kg)',
            r'(\d+\.?\d*)\s*(g|kg|ml|l)\s*(?:net|weight)',
        ]
        for pat in net_patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                qty_str = match.group(1).strip()
                if ' ' in qty_str:
                    qty_str = qty_str.split()[-1]
                fields['net_quantity'] = qty_str + ' ' + match.group(2)
                break

        # ---------- Manufacturing Date ----------
        mfg_patterns = [
            r'(?:mfg|manuf(?:acturing)?|date\s*of\s*(?:manufacture|packing)|manufacture\s*date)\s*[:]?\s*([\d/.-]+)',
            r'date\s*of\s*manufacture\s*[:]?\s*([\d/.-]+)',
            r'mfg\.?\s*date\s*[:]?\s*([\d/.-]+)',
        ]
        for pat in mfg_patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                fields['mfg_date'] = match.group(1)
                break

        # ---------- Expiry / Best Before ----------
        expiry_patterns = [
            r'(?:expiry|exp|best before|use by)\s*date\s*[:]?\s*([\d/.-]+)',
            r'expiry\s*date\s*[:]?\s*([\d/.-]+)',
            r'best\s*before\s*[:]?\s*([\d/.-]+(?:\s*(?:months?|years?|weeks?)?)?)',
        ]
        for pat in expiry_patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                fields['expiry_date'] = match.group(1).strip()
                break

        # ---------- Manufacturer / Packer / Importer ----------
        manuf_patterns = [
            r'(?:manufactured\s*by|manufacturer|packed\s*by|packer|repacked\s*by|importer|marketed\s*by)\s*[:]?\s*([^\n]+)',
            r'(?:mfg\.?|manuf\.?)\s*(?:by)?\s*[:]?\s*([^\n]+)',
        ]
        for pat in manuf_patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                fields['manufacturer'] = match.group(1).strip()
                break

        # ---------- Product Name ----------
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        product_keywords = ['coffee', 'sun rise', 'biscuit', 'chips', 'snack', 'oil', 'soyabean', 'roasted', 'grams', 'bahubali']
        product_candidate = None
        for line in lines:
            if any(kw in line.lower() for kw in product_keywords):
                product_candidate = line
                break
        if product_candidate:
            fields['product_name'] = product_candidate
        else:
            for line in lines:
                if not any(kw in line.lower() for kw in ['mrp', 'price', 'net', 'qty', 'weight', 'mfg', 'expiry',
                                                         'best before', 'manufactured', 'packed', 'imported',
                                                         'customer', 'date', 'batch', 'nutrition', 'ingredients',
                                                         'fssai', 'email', 'care', 'contact', 'repacked']):
                    fields['product_name'] = line
                    break

        # ---------- Consumer Care ----------
        care_patterns = [
            r'(?:customer\s*care|consumer\s*care|helpline|contact|toll\s*free)\s*(?:cell|no\.?|number)?\s*[:]?\s*([\d\s-]+)',
            r'ph\.?\s*no\.?\s*[:]?\s*([\d\s-]+)',
        ]
        for pat in care_patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                fields['consumer_care'] = match.group(1).strip()
                break

        # ---------- Country of Origin ----------
        origin_patterns = [
            r'(?:country\s*of\s*origin|origin|made\s*in)\s*[:]?\s*([^\n]+)',
        ]
        for pat in origin_patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                fields['country_of_origin'] = match.group(1).strip()
                break

        # ---------- Unit Sale Price ----------
        unit_patterns = [
            r'(?:unit\s*price|per\s*unit|unit\s*sale\s*price)\s*[:]?\s*[₹₹]?\s*(\d+\.?\d*)',
        ]
        for pat in unit_patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                fields['unit_sale_price'] = '₹' + match.group(1)
                break

        return fields