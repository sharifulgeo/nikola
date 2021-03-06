# -*- coding: utf-8 -*-

# Copyright © 2014-2015 Puneeth Chaganti and others.

# Permission is hereby granted, free of charge, to any
# person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the
# Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice
# shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
# OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import print_function
from datetime import datetime
import io
import os
import subprocess
import sys
from textwrap import dedent

from nikola.plugin_categories import Command
from nikola.plugins.command.check import real_scan_files
from nikola.utils import get_logger, req_missing, makedirs, unicode_str
from nikola.__main__ import main
from nikola import __version__


def uni_check_output(*args, **kwargs):
    o = subprocess.check_output(*args, **kwargs)
    return o.decode('utf-8')


def check_ghp_import_installed():
    try:
        subprocess.check_output(['ghp-import', '-h'])
    except OSError:
        # req_missing defaults to `python=True` — and it’s meant to be like this.
        # `ghp-import` is installed via pip, but the only way to use it is by executing the script it installs.
        req_missing(['ghp-import'], 'deploy the site to GitHub Pages')


class CommandGitHubDeploy(Command):
    """ Deploy site to GitHub Pages. """
    name = 'github_deploy'

    doc_usage = ''
    doc_purpose = 'deploy the site to GitHub Pages'
    doc_description = dedent(
        """\
        This command can be used to deploy your site to GitHub Pages.

        It uses ghp-import to do this task.

        """
    )

    logger = None

    def _execute(self, command, args):

        self.logger = get_logger(
            CommandGitHubDeploy.name, self.site.loghandlers
        )

        # Check if ghp-import is installed
        check_ghp_import_installed()

        # Build before deploying
        build = main(['build'])
        if build != 0:
            self.logger.error('Build failed, not deploying to GitHub')
            sys.exit(build)

        # Clean non-target files
        only_on_output, _ = real_scan_files(self.site)
        for f in only_on_output:
            os.unlink(f)

        # Commit and push
        self._commit_and_push()

        return

    def _commit_and_push(self):
        """ Commit all the files and push. """

        source = self.site.config['GITHUB_SOURCE_BRANCH']
        deploy = self.site.config['GITHUB_DEPLOY_BRANCH']
        remote = self.site.config['GITHUB_REMOTE_NAME']
        source_commit = uni_check_output(['git', 'rev-parse', source])
        commit_message = (
            'Nikola auto commit.\n\n'
            'Source commit: %s'
            'Nikola version: %s' % (source_commit, __version__)
        )
        output_folder = self.site.config['OUTPUT_FOLDER']

        command = ['ghp-import', '-n', '-m', commit_message, '-p', '-r', remote, '-b', deploy, output_folder]

        self.logger.info("==> {0}".format(command))
        try:
            subprocess.check_call(command)
        except subprocess.CalledProcessError as e:
            self.logger.error(
                'Failed GitHub deployment — command {0} '
                'returned {1}'.format(e.cmd, e.returncode)
            )
            sys.exit(e.returncode)

        self.logger.info("Successful deployment")

        # Store timestamp of successful deployment
        timestamp_path = os.path.join(self.site.config["CACHE_FOLDER"], "lastdeploy")
        new_deploy = datetime.utcnow()
        makedirs(self.site.config["CACHE_FOLDER"])
        with io.open(timestamp_path, "w+", encoding="utf8") as outf:
            outf.write(unicode_str(new_deploy.isoformat()))
