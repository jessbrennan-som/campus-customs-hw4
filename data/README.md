# The data pack goes here

The database and the product photos are not in the repository. Your instructor hands them out as `data.zip`. Unzip it so this folder looks like:

```
data/
├── README.md              (this file, from the repository)
├── campus_customs.db      the SQLite database
└── products/              the original product photos (.jpg)
```

From the `hw4` folder: `unzip data.zip -d .` if `data.zip` sits next to it, or drag the `data` folder's contents in by hand. The API creates its extra tables inside the database the first time it starts.

Optional: `backend/whiten_images.py` makes white-background copies of the photos in a `products-white/` folder here (see the main README).
