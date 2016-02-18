# -*- coding: latin-1 -*-
# stdlib
import os
import os.path
import tempfile
import unittest
from shutil import copyfile, rmtree

# project
from config import get_config, load_check_directory
from util import is_valid_hostname, windows_friendly_colon_split
from utils.pidfile import PidFile
from utils.platform import Platform

# No more hardcoded default checks
DEFAULT_CHECKS = []

class TestConfig(unittest.TestCase):
    def testWhiteSpaceConfig(self):
        """Leading whitespace confuse ConfigParser
        """
        agentConfig = get_config(cfg_path=os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                       'fixtures', 'badconfig.conf'),
                                 parse_args=False)
        self.assertEquals(agentConfig["dd_url"], "https://app.datadoghq.com")
        self.assertEquals(agentConfig["api_key"], "1234")
        self.assertEquals(agentConfig["nagios_log"], "/var/log/nagios3/nagios.log")
        self.assertEquals(agentConfig["graphite_listen_port"], 17126)
        self.assertTrue("statsd_metric_namespace" in agentConfig)

    def testGoodPidFie(self):
        """Verify that the pid file succeeds and fails appropriately"""

        pid_dir = tempfile.mkdtemp()
        program = 'test'

        expected_path = os.path.join(pid_dir, '%s.pid' % program)
        pid = "666"
        pid_f = open(expected_path, 'w')
        pid_f.write(pid)
        pid_f.close()

        p = PidFile(program, pid_dir)

        self.assertEquals(p.get_pid(), 666)
        # clean up
        self.assertEquals(p.clean(), True)
        self.assertEquals(os.path.exists(expected_path), False)

    def testBadPidFile(self):
        pid_dir = "/does-not-exist"

        p = PidFile('test', pid_dir)
        path = p.get_path()
        self.assertEquals(path, os.path.join(tempfile.gettempdir(), 'test.pid'))

        pid = "666"
        pid_f = open(path, 'w')
        pid_f.write(pid)
        pid_f.close()

        self.assertEquals(p.get_pid(), 666)
        self.assertEquals(p.clean(), True)
        self.assertEquals(os.path.exists(path), False)

    def testHostname(self):
        valid_hostnames = [
            u'i-123445',
            u'5dfsdfsdrrfsv',
            u'432498234234A'
            u'234234235235235235', # Couldn't find anything in the RFC saying it's not valid
            u'A45fsdff045-dsflk4dfsdc.ret43tjssfd',
            u'4354sfsdkfj4TEfdlv56gdgdfRET.dsf-dg',
            u'r'*255,
        ]

        not_valid_hostnames = [
            u'abc' * 150,
            u'sdf4..sfsd',
            u'$42sdf',
            u'.sfdsfds'
            u's™£™£¢ª•ªdfésdfs'
        ]

        for hostname in valid_hostnames:
            self.assertTrue(is_valid_hostname(hostname), hostname)

        for hostname in not_valid_hostnames:
            self.assertFalse(is_valid_hostname(hostname), hostname)

    def testWindowsSplit(self):
        # Make the function run as if it was on windows
        func = Platform.is_win32
        try:
            Platform.is_win32 = staticmethod(lambda : True)

            test_cases = [
                ("C:\\Documents\\Users\\script.py:C:\\Documents\\otherscript.py", ["C:\\Documents\\Users\\script.py","C:\\Documents\\otherscript.py"]),
                ("C:\\Documents\\Users\\script.py:parser.py", ["C:\\Documents\\Users\\script.py","parser.py"])
            ]

            for test_case, expected_result in test_cases:
                self.assertEqual(windows_friendly_colon_split(test_case), expected_result)
        finally:
            # cleanup
            Platform.is_win32 = staticmethod(func)

    def testDefaultChecks(self):
        checks = load_check_directory({"additional_checksd": "/etc/dd-agent/checks.d/"}, "foo")
        init_checks_names = [c.name for c in checks['initialized_checks']]

        for c in DEFAULT_CHECKS:
            self.assertTrue(c in init_checks_names)

class TestConfigLoadCheckDirectory(unittest.TestCase):

    TEMP_ETC_CHECKS_DIR = '/tmp/dd-agent-tests/etc/checks.d'
    TEMP_ETC_CONF_DIR = '/tmp/dd-agent-tests/etc/conf.d'
    TEMP_AGENT_CHECK_DIR = '/tmp/dd-agent-tests'
    TEMP_DIRS = [TEMP_ETC_CHECKS_DIR, TEMP_ETC_CONF_DIR, TEMP_AGENT_CHECK_DIR]
    FIXTURE_PATH = 'tests/core/fixtures/checks'

    def setUp(self):
        import config as Config
        self.patched_get_checksd_path = Config.get_checksd_path
        Config.get_checksd_path = lambda _: self.TEMP_AGENT_CHECK_DIR
        self.patched_get_confd_path = Config.get_confd_path
        Config.get_confd_path = lambda _: self.TEMP_ETC_CONF_DIR

        for _dir in self.TEMP_DIRS:
            if not os.path.exists(_dir):
                os.makedirs(_dir)

    def testConfigInvalid(self):
        copyfile('%s/invalid_conf.yaml' % self.FIXTURE_PATH,
            '%s/test_check.yaml' % self.TEMP_ETC_CONF_DIR)
        copyfile('%s/valid_check_1.py' % self.FIXTURE_PATH,
            '%s/test_check.py' % self.TEMP_AGENT_CHECK_DIR)
        checks = load_check_directory({"additional_checksd": self.TEMP_ETC_CHECKS_DIR}, "foo")
        self.assertEquals(1, len(checks['init_failed_checks']))

    def testConfigNotFound(self):
        copyfile('%s/valid_conf.yaml' % self.FIXTURE_PATH,
            '%s/test_check.yaml' % self.TEMP_ETC_CONF_DIR)
        checks = load_check_directory({"additional_checksd": self.TEMP_ETC_CHECKS_DIR}, "foo")
        self.assertEquals(0, len(checks['init_failed_checks']))
        self.assertEquals(0, len(checks['initialized_checks']))

    def testConfigAgentOnly(self):
        copyfile('%s/valid_conf.yaml' % self.FIXTURE_PATH,
            '%s/test_check.yaml' % self.TEMP_ETC_CONF_DIR)
        copyfile('%s/valid_check_1.py' % self.FIXTURE_PATH,
            '%s/test_check.py' % self.TEMP_AGENT_CHECK_DIR)
        checks = load_check_directory({"additional_checksd": self.TEMP_ETC_CHECKS_DIR}, "foo")
        self.assertEquals(1, len(checks['initialized_checks']))

    def testConfigETCOnly(self):
        copyfile('%s/valid_conf.yaml' % self.FIXTURE_PATH,
            '%s/test_check.yaml' % self.TEMP_ETC_CONF_DIR)
        copyfile('%s/valid_check_1.py' % self.FIXTURE_PATH,
            '%s/test_check.py' % self.TEMP_ETC_CHECKS_DIR)
        checks = load_check_directory({"additional_checksd": self.TEMP_ETC_CHECKS_DIR}, "foo")
        self.assertEquals(1, len(checks['initialized_checks']))

    def testConfigAgentETC(self):
        copyfile('%s/valid_conf.yaml' % self.FIXTURE_PATH,
            '%s/test_check.yaml' % self.TEMP_ETC_CONF_DIR)
        copyfile('%s/valid_check_2.py' % self.FIXTURE_PATH,
            '%s/test_check.py' % self.TEMP_AGENT_CHECK_DIR)
        copyfile('%s/valid_check_1.py' % self.FIXTURE_PATH,
            '%s/test_check.py' % self.TEMP_ETC_CHECKS_DIR)
        checks = load_check_directory({"additional_checksd": self.TEMP_ETC_CHECKS_DIR}, "foo")
        self.assertEquals(1, len(checks['initialized_checks']))
        self.assertEquals('valid_check_1', checks['initialized_checks'][0].check(None))

    def testConfigCheckNotAgentCheck(self):
        copyfile('%s/valid_conf.yaml' % self.FIXTURE_PATH,
            '%s/test_check.yaml' % self.TEMP_ETC_CONF_DIR)
        copyfile('%s/invalid_check_1.py' % self.FIXTURE_PATH,
            '%s/test_check.py' % self.TEMP_AGENT_CHECK_DIR)
        checks = load_check_directory({"additional_checksd": self.TEMP_ETC_CHECKS_DIR}, "foo")
        self.assertEquals(0, len(checks['init_failed_checks']))
        self.assertEquals(0, len(checks['initialized_checks']))

    def testConfigCheckImportError(self):
        copyfile('%s/valid_conf.yaml' % self.FIXTURE_PATH,
            '%s/test_check.yaml' % self.TEMP_ETC_CONF_DIR)
        copyfile('%s/invalid_check_2.py' % self.FIXTURE_PATH,
            '%s/test_check.py' % self.TEMP_AGENT_CHECK_DIR)
        checks = load_check_directory({"additional_checksd": self.TEMP_ETC_CHECKS_DIR}, "foo")
        self.assertEquals(1, len(checks['init_failed_checks']))

    def tearDown(self):
        import config as Config
        Config.get_checksd_path = self.patched_get_checksd_path
        Config.get_confd_path = self.patched_get_confd_path

        for _dir in self.TEMP_DIRS:
            rmtree(_dir)
