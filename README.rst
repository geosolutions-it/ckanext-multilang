
=============
ckanext-multilang
=============

The ckanext-multilang CKAN's extension provides a way to localize your CKAN's title and description 
contents for: Dataset, Resources, Organizations and Groups. This extension creates some new DB tables for this purpose 
containing localized contents in base of the configured CKAN's locales in configuration (the production.ini file).
So,  accessing the CKAN's GUI in 'en', for example, the User can create a new Dataset and automatically new localized records 
for that language will be created  in the multilang tables. In the same way, changing the GUI's language, from the CKAN's language 
dropdown, the User will be able to edit again the same Dataset in order to specify 'title' and 'description' of the Dataset for the 
new selected language.
In this way Dataset's title and description will automatically change simply switching the language from the CKAN's dropdonw.
 
The ckanext-multilang provides also an harvester built on the ckanext-spatial extension, and inherits all of its functionalities.
With this harvester, localized content for Dataset in CKAN can be retrieved form metadata that contains the gmd:PT_FreeText XML 
element (see the WIKI for more details).	


------------
Requirements
------------

The ckanext-multilang extension works with CKAN 2.4 or later.

------------------------
Development Installation
------------------------

To install ckanext-multilang:

1. Activate your CKAN virtual environment, for example::

     . /usr/lib/ckan/default/bin/activate

2. Go into your CKAN path for extension (like /usr/lib/ckan/default/src)

3. git clone https://github.com/geosolutions-it/ckanext-multilang.git

4. cd ckanext-multilang

5. python setup.py develop

6. paster --plugin=ckanext-multilang multilangdb initdb --config=/etc/ckan/default/production.ini

7. Add ``multilang`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/default/production.ini``).

4. Restart CKAN.

