The Zombies
==========

> Please don't bother trying to find her, she's not there.

\- The Zombies, ["She's Not There"](http://rock.genius.com/The-zombies-shes-not-there-lyrics)


This project audits the open data inventories of federal agencies. It can check for the presence of a JSON catalog at the required `/data.json` path on an agency domain and determine whether the catalog is valid JSON and if it follows the required schema (if the schema changes, this project will need to be updated to use the latest version). The Zombies real utility is in its ability to crawl the JSON data catalog and attempt to visit the URLs in the catalog as a means of seeing what is and is not where it is supposed to be.

This project tries to correct for some errors in data catalogs but fails on others when the issue indicates an issue with the catalog. This is mostly on purpose. Some types of URLs, such as FTP URLs, are not evaluated at this time.


## Installation

This project is driven by [Celery](http://www.celeryproject.org/) tasks, with Django providing an ORM and web views onto the results of the crawls. You'll want to familiarize yourself with the `celeryconfig.py` and `settings.py`. There is a Vagrant/ansible configuration for getting started quickly, but you will want to have plenty of RAM to run the various servers.

### Running via Vagrant/Ansible

If you have [Vagrant](https://www.vagrantup.com), [Virtualbox](https://www.virtualbox.org) and [Ansible](http://docs.ansible.com) installed, you can run the project in virtual machines. The Vagrantfile defines 4 machines:

- Celery workers server
- Worker queue server
- Database server
- Web server

In order to run these machines, you'll need `Virtualbox` and `ansible` installed.  You will also need to git checkout the `ansible-common-roles` submodule, so you will probably need to run 'git submodule init && git submodule update' before attempting to provision servers using Vagrant. The Worker and queue machines were configured with 1GB RAM each to facilitate running many simultaneous tasks, but these settings haven't been adjusted since some of the memory-intensive tasks have been optimized.

### Running locally

If you don't want to the project using virtual machines, you'll need to make sure you have PostgreSQL, Redis, and RabbitMQ. You could try to use Redis for double-duty in place of RabbitMQ, but YMMV.

This code was developed against Python 2.7.x since *greenlet*, the concurrency library we're using with Celery, wasn't Python3 compatible at the time. The following should create a virtual environment with your python 2.7.x interpreter.

```shell
$ mkvirtualenv thezombies
$ pip install -r dev-requirements.txt
```

## Running tasks

The meat of this project is the tasks living in *thezombies* app. There are tasks to validate JSON data catalogs against schemas (see the `schema` directory), tasks to inspect a catalog for URLs and tasks for inspecting URLs in various ways. These tasks are meant to recover from (and usually record errors) such as HTTP timeouts or invalid SSL certificate chains. The validation tasks inspect "dataset" objects in the catalogs using a streaming JSON parser, so the overall catalog isn't validated. We also try to recover from some kinds of invalid or poorly encoded JSON so that we can continue to look for URLs to inspect even if there are problems with the JSON.

`thezombies.tasks.crawl.crawl_agency_catalog` is an entry point for crawling a single Agency's catalog and inspecting the URLs contained within. Depending on the size of the agency's catalog and the number of links, this could take many minutes or more.

`thezombies.tasks.validation.validate_catalog_datasets` is an entry point for validating an agency's data catalog.

Remember to run these tasks using one of the Celery task methods, such as *delay* or *apply_async*, so that these tasks can be spun up and run on workers. Many of the tasks spawn subtasks, so it may not be an issue to call some of these functions directly, but they are all designed to be called as Celery tasks. Tasks should return some information to help retrieve information later, such as the Django object ids.

## Notes on the data

The project is centered around *Audits* which which relate to an agency. *Probe* objects are associated with an Audit and record information from tasks. Both audits and probes have type fields that can be used to describe their purpose (validation, JSON parsing, URL inspection, etc). *URLInspection* objects record information about URLs that are inspected, and can be related to Probes.
