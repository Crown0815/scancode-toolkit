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
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import codecs
from collections import OrderedDict
import json
import os

from commoncode.system import on_linux


def remove_dates(scan_result):
    """
    Remove date fields from scan.
    """
    for scanned_file in scan_result['files']:
        scanned_file.pop('date', None)


def clean_errors(scan_results):
    """
    Clean error fields from scan by keeping only the first and last line
    (removing the stack traces).
    """

    def clean(_errors):
        """Modify the __errors list in place"""
        for _i, _error in enumerate(_errors[:]):
            _error_split = _error.splitlines(True)
            if len(_error_split) <= 1:
                continue
            # keep first and last line
            _clean_error = ''.join([_error_split[0] + _error_split[-1]])
            _errors[_i] = _clean_error

    top_level = scan_results.get('scan_errors')
    if top_level:
        clean(top_level)

    for result in scan_results['files']:
        file_level = result.get('scan_errors')
        if file_level:
            clean(file_level)


def check_json_scan(expected_file, result_file, regen=False,
                    strip_dates=False, clean_errs=True):
    """
    Check the scan result_file JSON results against the expected_file expected
    JSON results. Removes references to test_dir for the comparison. If regen is
    True the expected_file WILL BE overwritten with the results. This is
    convenient for updating tests expectations. But use with caution.
    """
    scan_results = _load_json_result(result_file)

    if strip_dates:
        remove_dates(scan_results)

    if clean_errs:
        clean_errors(scan_results)

    if regen:
        with open(expected_file, 'wb') as reg:
            json.dump(scan_results, reg, indent=2, separators=(',', ': '))

    expected = _load_json_result(expected_file)

    if strip_dates:
        remove_dates(expected)
    if clean_errs:
        clean_errors(expected)

    # NOTE we redump the JSON as a string for a more efficient comparison of
    # failures
    # TODO: remove sort, this should no longer be needed
    expected = json.dumps(expected, indent=2, sort_keys=True, separators=(',', ': '))
    scan_results = json.dumps(scan_results, indent=2, sort_keys=True, separators=(',', ': '))
    assert expected == scan_results


def _load_json_result(result_file):
    """
    Load the result file as utf-8 JSON
    Sort the results by location.
    """
    with codecs.open(result_file, encoding='utf-8') as res:
        scan_result = json.load(res, object_pairs_hook=OrderedDict)

    if scan_result.get('scancode_version'):
        del scan_result['scancode_version']

    # TODO: remove sort, this should no longer be needed
    scan_result['files'].sort(key=lambda x: x['path'])
    return scan_result


def run_scan_plain(options, cwd=None, test_mode=True):
    """
    Run a scan as a plain subprocess. Return rc, stdout, stderr.
    """
    from commoncode.command import execute
    import scancode

    if test_mode and '--test-mode' not in options:
        options.append('--test-mode')

    scmd = b'scancode' if on_linux else 'scancode'
    scan_cmd = os.path.join(scancode.root_dir, scmd)
    return execute(scan_cmd, options, cwd=cwd)


def run_scan_click(options, monkeypatch=None, test_mode=True):
    """
    Run a scan as a Click-controlled subprocess
    If monkeypatch is provided, a tty with a size (80, 43) is mocked.
    Return a click.testing.Result object.
    """
    import click
    from click.testing import CliRunner
    from scancode import cli

    if test_mode and '--test-mode' not in options:
        options.append('--test-mode')

    if monkeypatch:
        monkeypatch.setattr(click._termui_impl, 'isatty', lambda _: True)
        monkeypatch.setattr(click , 'get_terminal_size', lambda : (80, 43,))
    runner = CliRunner()

    return runner.invoke(cli.scancode, options, catch_exceptions=False)
