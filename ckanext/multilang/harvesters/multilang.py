
import json

import logging
import ckan.lib.search as search

from ckan import model
from ckan.model import Session
from ckan.model import meta

from ckanext.multilang.model import PackageMultilang

from ckan.plugins.core import SingletonPlugin

from ckanext.spatial.lib.csw_client import CswService
from ckanext.spatial.harvesters.csw import CSWHarvester

from ckanext.spatial.model import ISODocument
from ckanext.spatial.model import ISOElement

from ckan.logic import ValidationError, NotFound, get_action

from pylons import config
from datetime import datetime

log = logging.getLogger(__name__)

# Extend the ISODocument definitions by adding some more useful elements

log.info('CSW Multilang harvester: extending ISODocument with PT_FreeText')
class ISOTextGroup(ISOElement):
    elements = [
        ISOElement(
            name="text",
            search_paths=[
                "gmd:LocalisedCharacterString/text()"
            ],
            multiplicity="1",
        ),
        ISOElement(
            name="locale",
            search_paths=[
                "gmd:LocalisedCharacterString/@locale"
            ],
            multiplicity="1",
        )
    ]

ISODocument.elements.append(
    ISOTextGroup(
        name="title-text",
        search_paths=[
            "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gmd:PT_FreeText/gmd:textGroup",
            "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gmd:PT_FreeText/gmd:textGroup"
        ],
        multiplicity="1..*",
    )
)

ISODocument.elements.append(
    ISOTextGroup(
        name="abstract-text",
        search_paths=[
            "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract/gmd:PT_FreeText/gmd:textGroup",
            "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:abstract/gmd:PT_FreeText/gmd:textGroup"
        ],
        multiplicity="1..*",
    )
)

class MultilangHarvester(CSWHarvester, SingletonPlugin):

    _package_dict = None 

    _ckan_locales_mapping = {
        'ita': 'it',
        'ger': 'de'
    }

    def info(self):
        return {
            'name': 'multilang',
            'title': 'CSW server (Multilang)',
            'description': 'Harvests CWS with Multilang',
            'form_config_interface': 'Text'
        }

    ##
    ## Saves in memory the package_dict localised texts 
    ##
    def get_package_dict(self, iso_values, harvest_object):
        package_dict = super(MultilangHarvester, self).get_package_dict(iso_values, harvest_object)        
        
        if iso_values["abstract-text"] and iso_values["title-text"]:

            log.debug('::::: Collecting localised data from the metadata abstract :::::')
            localised_abstracts = []
            for abstract_entry in iso_values["abstract-text"]:
                if abstract_entry['text'] and abstract_entry['locale'].lower()[1:]:
                    if self._ckan_locales_mapping[abstract_entry['locale'].lower()[1:]]:
                        localised_abstracts.append({
                            'text': abstract_entry['text'],
                            'locale': self._ckan_locales_mapping[abstract_entry['locale'].lower()[1:]]
                        })
                    else:
                        log.warning('Locale Mapping not found for metadata abstract, entry skipped!')
                else:
                    log.warning('TextGroup data not available for metadata abstract, entry skipped!')

            log.debug('::::: Collecting localized data from the metadata title :::::')
            localised_titles = []
            for title_entry in iso_values["title-text"]:
                if title_entry['text'] and title_entry['locale'].lower()[1:]:
                    if self._ckan_locales_mapping[title_entry['locale'].lower()[1:]]:
                        localised_titles.append({
                            'text': title_entry['text'],
                            'locale': self._ckan_locales_mapping[title_entry['locale'].lower()[1:]]
                        })
                    else:
                        log.warning('Locale Mapping not found for metadata title, entry skipped!')
                else:
                    log.warning('TextGroup data not available for metadata title, entry skipped!')
            
            localised_titles.append({
                'text': iso_values['title'],
                'locale': self._ckan_locales_mapping[iso_values["metadata-language"].lower()]
            })

            localised_abstracts.append({
                'text': iso_values['abstract'],
                'locale': self._ckan_locales_mapping[iso_values["metadata-language"].lower()]
            })

            self._package_dict = {
                'localised_titles': localised_titles,
                'localised_abstracts': localised_abstracts
            }

            log.info('::::::::: Localised _package_dict saved in memory :::::::::')

        # End of processing, return the modified package
        return package_dict

    def after_import_stage(self, package_dict):        
        log.info('::::::::: Performing after_import_stage  persist operation for localised dataset content :::::::::')

        if self._package_dict:            
            session = Session

            try:
                package_id = package_dict.get('id')

                rows = session.query(PackageMultilang).filter(PackageMultilang.package_id == package_id).all()

                if not rows:
                    log.info('::::::::: Adding new localised object to the package_multilang table :::::::::')
                    
                    log.debug('::::: Persisting default metadata locale :::::')

                    log.debug('::::: Persisting tile locales :::::')
                    for title in self._package_dict.get('localised_titles'):
                        session.add_all([
                            PackageMultilang(package_id=package_id, field='title', field_type='localized', lang=title.get('locale'), text=title.get('text')),
                        ])

                    log.debug('::::: Persisting abstract locales :::::')
                    for abstract in self._package_dict.get('localised_abstracts'):
                        session.add_all([
                            PackageMultilang(package_id=package_id, field='notes', field_type='localized', lang=abstract.get('locale'), text=abstract.get('text')),
                        ])

                    session.commit()

                    log.info('::::::::: OBJECT PERSISTED SUCCESSFULLY :::::::::')

                else:
                    log.info('::::::::: Updating localised object in the package_multilang table :::::::::')
                    for row in rows:
                        if row.field == 'title': 
                            titles = self._package_dict.get('localised_titles')
                            for title in titles:
                                if title.get('locale') == row.lang:
                                    row.text = title.get('text')
                        elif row.field == 'notes': 
                            abstracts = self._package_dict.get('localised_abstracts')
                            for abstract in abstracts:
                                if abstract.get('locale') == row.lang:
                                    row.text = abstract.get('text')

                        row.save()

                    log.info('::::::::: OBJECT UPDATED SUCCESSFULLY :::::::::') 

                pass
            except Exception, e:
                # on rollback, the same closure of state
                # as that of commit proceeds. 
                session.rollback()

                log.error('Exception occurred while persisting DB objects: %s', e)
                raise

        # Updating Solr Index
        if package_dict:
            log.info("::: UPDATING SOLR INDEX :::")
            # solr update here
            psi = search.PackageSearchIndex()

            # update the solr index in batches
            BATCH_SIZE = 50

            def process_solr(q):
                # update the solr index for the query
                query = search.PackageSearchQuery()
                q = {
                    'q': q,
                    'fl': 'data_dict',
                    'wt': 'json',
                    'fq': 'site_id:"%s"' % config.get('ckan.site_id'),
                    'rows': BATCH_SIZE
                }

                for result in query.run(q)['results']:
                    data_dict = json.loads(result['data_dict'])
                    if data_dict['owner_org'] == package_dict.get('owner_org'):
                        psi.index_package(data_dict, defer_commit=True)

            count = 0
            q = []
            
            q.append('id:"%s"' % (package_dict.get('id')))
            count += 1
            if count % BATCH_SIZE == 0:
                process_solr(' OR '.join(q))
                q = []

            if len(q):
                process_solr(' OR '.join(q))
            # finally commit the changes
            psi.commit()
        else:
            log.warning("::: package_dict is None: SOLR INDEX CANNOT BE UPDATED! :::")


        return