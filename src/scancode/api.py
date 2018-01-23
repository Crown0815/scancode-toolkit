#
# Copyright (c) 2018 nexB Inc. and others. All rights reserved.
# http://nexb.com and https://github.com/nexB/scancode-toolkit/
# The ScanCode software is licensed under the Apache License version 2.0.
# Data generated with ScanCode require an acknowledgment.
# ScanCode is a trademark of nexB Inc.
#
# You may not use this software except in compliance with the License.
# You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#
# When you publish or redistribute any data created with ScanCode or any ScanCode
# derivative work, you must accompany this data with the following acknowledgment:
#
#  Generated with ScanCode and provided on an "AS IS" BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, either express or implied. No content created from
#  ScanCode should be considered or used as legal advice. Consult an Attorney
#  for any legal advice.
#  ScanCode is a free software code scanning tool from nexB Inc. and others.
#  Visit https://github.com/nexB/scancode-toolkit/ for support and download.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
from os.path import getsize

from commoncode.filetype import get_last_modified_date
from commoncode.filetype import get_type as get_simple_type
from commoncode.filetype import is_file as filetype_is_file
from commoncode.fileutils import file_name
from commoncode.fileutils import splitext
from commoncode.hash import multi_checksums
from commoncode.system import on_linux
from typecode.contenttype import get_type


"""
Main scanning functions.

Each scanner is a function that accepts a location and returns a sequence of
mappings as results.

Note: this API is unstable and still evolving.
"""


def get_copyrights(location, **kwargs):
    """
    Return a list of mappings for copyright detected in the file at `location`.
    """
    from cluecode.copyrights import detect_copyrights
    results = []
    for copyrights, authors, _years, holders, start_line, end_line in detect_copyrights(location):
        result = OrderedDict()
        results.append(result)
        # FIXME: we should call this copyright instead, and yield one item per statement
        result['statements'] = copyrights
        result['holders'] = holders
        result['authors'] = authors
        result['start_line'] = start_line
        result['end_line'] = end_line
    return results


def get_emails(location, **kwargs):
    """
    Return a list of mappings for emails detected in the file at `location`.
    """
    from cluecode.finder import find_emails
    results = []
    for email, line_num  in find_emails(location):
        if not email:
            continue
        result = OrderedDict()
        results.append(result)
        result['email'] = email
        result['start_line'] = line_num
        result['end_line'] = line_num
    return results


def get_urls(location, **kwargs):
    """
    Return a list of mappings for urls detected in the file at `location`.
    """
    from cluecode.finder import find_urls
    results = []
    for urls, line_num  in find_urls(location):
        if not urls:
            continue
        result = OrderedDict()
        results.append(result)
        result['url'] = urls
        result['start_line'] = line_num
        result['end_line'] = line_num
    return results


DEJACODE_LICENSE_URL = 'https://enterprise.dejacode.com/urn/urn:dje:license:{}'
SPDX_LICENSE_URL = 'https://spdx.org/licenses/{}'


def get_licenses(location, min_score=0, include_text=False, diag=False,
                 license_url_template=DEJACODE_LICENSE_URL,
                 cache_dir=None,
                 **kwargs):
    """
    Return a list of mappings for licenses detected in the file at `location`.

    `minimum_score` is a minimum score threshold from 0 to 100. The default is 0
    means that all license matches are returned. Otherwise, matches with a score
    below `minimum_score` are returned.

    if `include_text` is True, matched text is included in the returned data.

    If `diag` is True, additional license match details are returned with the
    matched_rule key of the returned mapping.
    """
    if not cache_dir:
        from scancode_config import scancode_cache_dir as cache_dir

    from licensedcode.cache import get_index
    from licensedcode.cache import get_licenses_db

    idx = get_index(cache_dir)
    licenses = get_licenses_db()

    results = []
    for match in idx.match(location=location, min_score=min_score):
        if include_text:
            matched_text = match.matched_text(whole_lines=False)

        for license_key in match.rule.licenses:
            lic = licenses.get(license_key)
            result = OrderedDict()
            results.append(result)
            result['key'] = lic.key
            result['score'] = match.score()
            result['short_name'] = lic.short_name
            result['category'] = lic.category
            result['owner'] = lic.owner
            result['homepage_url'] = lic.homepage_url
            result['text_url'] = lic.text_urls[0] if lic.text_urls else ''
            result['reference_url'] = license_url_template.format(lic.key)
            spdx_key = lic.spdx_license_key
            result['spdx_license_key'] = spdx_key
            if spdx_key:
                spdx_key = lic.spdx_license_key.rstrip('+')
                spdx_url = SPDX_LICENSE_URL.format(spdx_key)
            else:
                spdx_url = ''
            result['spdx_url'] = spdx_url
            result['start_line'] = match.start_line
            result['end_line'] = match.end_line
            matched_rule = result['matched_rule'] = OrderedDict()
            matched_rule['identifier'] = match.rule.identifier
            matched_rule['license_choice'] = match.rule.license_choice
            matched_rule['licenses'] = match.rule.licenses
            # FIXME: for sanity these should always be included???
            if diag:
                matched_rule['matcher'] = match.matcher
                matched_rule['rule_length'] = match.rule.length
                matched_rule['matched_length'] = match.ilen()
                matched_rule['match_coverage'] = match.coverage()
                matched_rule['rule_relevance'] = match.rule.relevance
            # FIXME: for sanity this should always be included?????
            if include_text:
                result['matched_text'] = matched_text

    return results


def get_package_info(location, **kwargs):
    """
    Return a list of mappings for package information detected in the file at
    `location`.
    """
    from packagedcode.recognize import recognize_package
    package = recognize_package(location)
    results = []
    if package:
        results.append(package.to_dict())
    return results


def get_file_info(location, **kwargs):
    """
    Return a list of mappings for file information collected for the file or
    directory at `location`.
    """
    result = OrderedDict()
    results = [result]

    collector = get_type(location)
    result['type'] = get_simple_type(location, short=False)
    is_file = filetype_is_file(location)

    if is_file:
        base_name, extension = splitext(location)
    else:
        # directories have no extension
        base_name = file_name(location)
        extension = b'' if on_linux else ''
    result['base_name'] = base_name
    result['extension'] = extension

    if is_file:
        result['date'] = get_last_modified_date(location) or None
        result['size'] = getsize(location) or 0
        result.update(multi_checksums(location, ('sha1', 'md5',)))
        result['mime_type'] = collector.mimetype_file or None
        result['file_type'] = collector.filetype_file or None
        result['programming_language'] = collector.programming_language or None
        result['is_binary'] = bool(collector.is_binary)
        result['is_text'] = bool(collector.is_text)
        result['is_archive'] = bool(collector.is_archive)
        result['is_media'] = bool(collector.is_media)
        result['is_source'] = bool(collector.is_source)
        result['is_script'] = bool(collector.is_script)

    return results


def extract_archives(location, recurse=True):
    """
    Yield ExtractEvent while extracting archive(s) and compressed files at
    `location`. If `recurse` is True, extract nested archives-in-archives
    recursively.
    Archives and compressed files are extracted in a directory named
    "<file_name>-extract" created in the same directory as the archive.
    Note: this API is returning an iterable and NOT a sequence.
    """
    from extractcode.extract import extract
    from extractcode import default_kinds
    for xevent in extract(location, kinds=default_kinds, recurse=recurse):
        yield xevent
