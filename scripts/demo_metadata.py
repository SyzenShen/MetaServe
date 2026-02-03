import os
import sys
import django
from pathlib import Path

# Set up Django environment
# Assuming this script is run from project root or scripts/ directory
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'file_project.settings')
django.setup()

from file_upload.metadata_extractor import MetadataExtractor

def run_demo():
    extractor = MetadataExtractor()
    
    # 1. Create and Test FASTA
    fasta_path = 'demo_test.fasta'
    print(f"\n[1] Creating dummy FASTA file: {fasta_path}")
    with open(fasta_path, 'w') as f:
        f.write('>seq1 Homo sapiens (Human) gene marker\n')
        f.write('ATGCGTAGCTAGCTAGCTAGCTAGCTAGCT\n')
        f.write('>seq2 Mus musculus (Mouse) similar sequence\n')
        f.write('CGTACGTAGCTAGCTAGCTAGCTAGCTAGC\n')
    
    print(">>> Extracting metadata...")
    meta_fasta = extractor.extract_metadata(fasta_path, 'FASTA')
    print("Result:", meta_fasta)
    
    # 2. Create and Test CSV
    csv_path = 'demo_test.csv'
    print(f"\n[2] Creating dummy CSV file: {csv_path}")
    with open(csv_path, 'w') as f:
        f.write('GeneID,Symbol,Log2FC,PValue,Description\n')
        f.write('101,EGFR,2.5,0.001,Epidermal growth factor receptor\n')
        f.write('102,TP53,-1.2,0.05,Tumor protein p53\n')
        
    print(">>> Extracting metadata...")
    meta_csv = extractor.extract_metadata(csv_path, 'CSV')
    print("Result:", meta_csv)
    
    # Cleanup
    if os.path.exists(fasta_path): os.remove(fasta_path)
    if os.path.exists(csv_path): os.remove(csv_path)
    print("\n[Done] Demo finished and temporary files cleaned up.")

if __name__ == '__main__':
    run_demo()
