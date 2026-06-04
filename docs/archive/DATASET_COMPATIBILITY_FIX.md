This project was patched to support the vNext structured dataset format.

Supported formats:
1. Old flat-array dataset
2. New structured dataset with:
   {
     "dataset_metadata": {},
     "bylaws": [...]
   }

The importer now safely reads:
data["bylaws"]
when structured datasets are used.
