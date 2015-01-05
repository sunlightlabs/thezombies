The Zombies
==========

> Please don't bother trying to find her, she's not there.

\- The Zombies, ["She's Not There"](http://rock.genius.com/The-zombies-shes-not-there-lyrics)


This project audits the open data inventories of federal agencies. It can check for the presence of a JSON catalog at the required `/data.json` path on an agency domain and determine whether the catalog is valid JSON and if it follows the required schema (if the schema changes, this project will need to be updated to use the latest version). The Zombies real utility is in its ability to crawl the JSON data catalog and attempt to visit the URLs in the catalog as a means of seeing what is and is not where it is supposed to be.

This project tries to correct for some errors in data catalogs but fails on others when the issue indicates an issue with the catalog. This is mostly on purpose. Some types of URLs, such as FTP URLs, are not evaluated at this time.
