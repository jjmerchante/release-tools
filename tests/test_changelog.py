#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2019 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>..
#
# Authors:
#     Santiago Dueñas <sduenas@bitergia.com>
#

import os
import unittest
import unittest.mock

import click.testing
import yaml

from release_tools import changelog


CHANGELOG_ENTRIES_DIR_ERROR = (
    "Error: Changelog entries directory is needed to continue."
)
CHANGELOG_ENTRY_ALREADY_EXISTS_ERROR = (
    "Error: Changelog entry new-change.yml already exists. Use '--overwrite' to replace it."
)
EMPTY_CONTENT_ERROR = (
    "Error: Aborting due to empty entry content"
)
INVALID_TITLE_ERROR = (
    "Error: Invalid value for \"-t\" / \"--title\": title cannot be empty"
)
INVALID_CATEGORY_ERROR = (
    "Error: Invalid value for \"-c\" / \"--category\": "
    "valid options are "
    "['added', 'fixed', 'changed', 'deprecated', 'removed', 'security', 'performance', 'other']"
)
INVALID_CATEGORY_INDEX_ERROR = (
    "Error: Invalid value for \"-c\" / \"--category\": please select an index between 1 and 8"
)


class TestChangelog(unittest.TestCase):
    """Unit tests for changelog script"""

    @unittest.mock.patch('release_tools.changelog.Project')
    def test_entry_is_created(self, mock_project):
        """Check whether a changelog entry is created"""

        runner = click.testing.CliRunner()
        user_input = "new change\n1\ny"

        with runner.isolated_filesystem() as fs:
            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_project.return_value.unreleased_changes_path = dirpath

            result = runner.invoke(changelog.changelog, ['--no-editor'],
                                   input=user_input)
            self.assertEqual(result.exit_code, 0)

            # Check entry and contents
            filepath = os.path.join(dirpath, 'new-change.yml')

            self.assertEqual(os.path.exists(filepath), True)

            with open(filepath, mode='r') as fd:
                entry = yaml.safe_load(fd)
                self.assertEqual(entry['title'], 'new change')
                self.assertEqual(entry['category'], 'added')
                self.assertEqual(entry['author'], None)
                self.assertEqual(entry['pull_request'], None)
                self.assertEqual(entry['notes'], None)

    @unittest.mock.patch('release_tools.changelog.Project')
    def test_entry_is_not_overwritten(self, mock_project):
        """Check whether an existing changelog entry is not replaced"""

        runner = click.testing.CliRunner(mix_stderr=False)
        user_input = "y\n"

        with runner.isolated_filesystem() as fs:
            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_project.return_value.unreleased_changes_path = dirpath

            # Create an entry first
            params = [
                '--title', 'new change',
                '--category', 'fixed',
                '--no-editor'
            ]
            result = runner.invoke(changelog.changelog, params,
                                   input=user_input)
            self.assertEqual(result.exit_code, 0)

            # Try to replace it
            params = [
                '--title', 'new change',
                '--category', 'added',
                '--no-editor'
            ]
            result = runner.invoke(changelog.changelog, params)
            self.assertEqual(result.exit_code, 1)

            lines = result.stderr.split('\n')
            self.assertEqual(lines[-2], CHANGELOG_ENTRY_ALREADY_EXISTS_ERROR)

            # Check entry and contents. They did not change.
            filepath = os.path.join(dirpath, 'new-change.yml')

            with open(filepath, mode='r') as fd:
                entry = yaml.safe_load(fd)
                self.assertEqual(entry['title'], 'new change')
                self.assertEqual(entry['category'], 'fixed')
                self.assertEqual(entry['author'], None)
                self.assertEqual(entry['pull_request'], None)
                self.assertEqual(entry['notes'], None)

    @unittest.mock.patch('release_tools.changelog.Project')
    def test_overwrite_entry(self, mock_project):
        """Check if it overwrites am existing changelog entry when the proper flag is set"""

        runner = click.testing.CliRunner(mix_stderr=False)
        user_input = "y\n"

        with runner.isolated_filesystem() as fs:
            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_project.return_value.unreleased_changes_path = dirpath

            # Create an entry first
            params = [
                '--title', 'new change',
                '--category', 'fixed',
                '--no-editor'
            ]
            result = runner.invoke(changelog.changelog, params,
                                   input=user_input)
            self.assertEqual(result.exit_code, 0)

            # Check entry and contents
            filepath = os.path.join(dirpath, 'new-change.yml')

            with open(filepath, mode='r') as fd:
                entry = yaml.safe_load(fd)
                self.assertEqual(entry['title'], 'new change')
                self.assertEqual(entry['category'], 'fixed')
                self.assertEqual(entry['author'], None)
                self.assertEqual(entry['pull_request'], None)
                self.assertEqual(entry['notes'], None)

            # Try to replace it
            params = [
                '--title', 'new change',
                '--category', 'added',
                '--overwrite', '--no-editor'
            ]
            result = runner.invoke(changelog.changelog, params)
            self.assertEqual(result.exit_code, 0)

            # Check entry and contents. They should have changed
            with open(filepath, mode='r') as fd:
                entry = yaml.safe_load(fd)
                self.assertEqual(entry['title'], 'new change')
                self.assertEqual(entry['category'], 'added')
                self.assertEqual(entry['author'], None)
                self.assertEqual(entry['pull_request'], None)
                self.assertEqual(entry['notes'], None)

    @unittest.mock.patch('release_tools.changelog.Project')
    @unittest.mock.patch('release_tools.changelog.click.edit')
    def test_abort_entry_empty(self, mock_edit, mock_project):
        """Check if it stops the process when the content of the entry to create is empty"""

        runner = click.testing.CliRunner(mix_stderr=False)
        user_input = "new change\n1\ny"

        with runner.isolated_filesystem() as fs:
            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_project.return_value.unreleased_changes_path = dirpath

            mock_edit.return_value = ""

            result = runner.invoke(changelog.changelog,
                                   input=user_input)
            self.assertEqual(result.exit_code, 1)

            lines = result.stderr.split('\n')
            self.assertEqual(lines[-2], EMPTY_CONTENT_ERROR)

    @unittest.mock.patch('release_tools.changelog.Project')
    def test_create_entries_dir(self, mock_project):
        """Check if the entries dir is created when it does not exist"""

        runner = click.testing.CliRunner()

        # 'y' means the user wants to create the dir when asked
        user_input = "new change\n1\ny"

        with runner.isolated_filesystem() as fs:
            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_project.return_value.unreleased_changes_path = dirpath

            result = runner.invoke(changelog.changelog, ['--no-editor'],
                                   input=user_input)
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(os.path.exists(dirpath), True)

            filepath = os.path.join(dirpath, 'new-change.yml')
            self.assertEqual(os.path.exists(filepath), True)

    @unittest.mock.patch('release_tools.changelog.Project')
    def test_entries_dir_not_created(self, mock_project):
        """Check if it stops working when the entries dir is not created"""

        runner = click.testing.CliRunner(mix_stderr=False)

        # 'n' means the user refuses to create the dir when asked
        user_input = "new change\n1\nn"

        with runner.isolated_filesystem() as fs:
            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_project.return_value.unreleased_changes_path = dirpath

            result = runner.invoke(changelog.changelog, ['--no-editor'],
                                   input=user_input)
            self.assertEqual(result.exit_code, 1)

            lines = result.stderr.split('\n')
            self.assertEqual(lines[-2], CHANGELOG_ENTRIES_DIR_ERROR)

            # Nothing was created in the directory
            self.assertEqual(len(os.listdir(fs)), 0)

    def test_invalid_title(self):
        """Check whether title param is validated correctly"""

        runner = click.testing.CliRunner(mix_stderr=False)

        # Empty titles are not allowed
        result = runner.invoke(changelog.changelog, ['--title', ''])
        self.assertEqual(result.exit_code, 2)

        lines = result.stderr.split('\n')
        self.assertEqual(lines[-2], INVALID_TITLE_ERROR)

        # Only whitespaces are not allowed
        result = runner.invoke(changelog.changelog, ['--title', ' '])
        self.assertEqual(result.exit_code, 2)

        lines = result.stderr.split('\n')
        self.assertEqual(lines[-2], INVALID_TITLE_ERROR)

        # Only control characters are not allowed
        result = runner.invoke(changelog.changelog, ['--title', '\n\r\n'])
        self.assertEqual(result.exit_code, 2)
        self.assertEqual(lines[-2], INVALID_TITLE_ERROR)

    def test_invalid_category(self):
        """Check whether category param is validated correctly"""

        runner = click.testing.CliRunner(mix_stderr=False)

        # Invalid categories are not allowed
        result = runner.invoke(changelog.changelog, ['--category', 'invalid'])
        self.assertEqual(result.exit_code, 2)

        lines = result.stderr.split('\n')
        self.assertEqual(lines[-2], INVALID_CATEGORY_ERROR)

        # Invalid indexes are not allowed
        result = runner.invoke(changelog.changelog, ['--category', '42'])
        self.assertEqual(result.exit_code, 2)

        lines = result.stderr.split('\n')
        self.assertEqual(lines[-2], INVALID_CATEGORY_INDEX_ERROR)


if __name__ == '__main__':
    unittest.main()