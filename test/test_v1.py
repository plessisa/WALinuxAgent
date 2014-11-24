# Copyright 2014 Microsoft Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requires Python 2.4+ and Openssl 1.0+
#
# Implements parts of RFC 2131, 1541, 1497 and
# http://msdn.microsoft.com/en-us/library/cc227282%28PROT.10%29.aspx
# http://msdn.microsoft.com/en-us/library/cc227259%28PROT.13%29.aspx

import env
import test.tools as tools
from tools import *
import uuid
import unittest
import os
import time
import walinuxagent.logger as logger
import walinuxagent.protocol.v1 as v1
from  walinuxagent.utils.osutil import CurrOSInfo, CurrOS
from test_version import VersionInfoSample
from test_goalstate import GoalStateSample
from test_hostingenv import HostingEnvSample
from test_sharedconfig import SharedConfigSample
from test_certificates import CertificatesSample
from test_extensionsconfig import ExtensionsConfigSample, ManifestSample

def MockHttpGet(url, headers=None, maxRetry=1):
    content = None
    if "versions" in url:
        content = VersionInfoSample
    elif "goalstate" in url:
        content = GoalStateSample
    elif "hostingenvuri" in url:
        content = HostingEnvSample
    elif "sharedconfiguri" in url:
        content = SharedConfigSample
    elif "certificatesuri" in url:
        content = CertificatesSample
    elif "extensionsconfiguri" in url:
        content = ExtensionsConfigSample
    elif "manifest.xml" in url:
        content = ManifestSample
    else:
        raise Exception("Bad url {0}".format(url))
    return MockResp(content)

class MockResp(object):
    def __init__(self, content):
        self.content = content
    def read(self):
        return self.content

MockHttpPut = MockFunc('HttpPut')
MockHttpPost = MockFunc('HttpPost')
MockIsFile = MockFunc('isfile', True)
MockIsResponsive = MockFunc('isResponsive', True)

StatusFileSample = """
"status":{
"status":"success",
"formattedMessage":{
"lang":"en-US",
"message":"Scriptisfinished"
},
"operation":"Enable",
"code":"0",
"name":"ExampleHandlerLinux"
}
"""

HeartbeatSample = """
[{
"version":1.0,
"heartbeat":{
"status":"ready",
"code":0,
"Message":"Extension is running"
}
}]
"""
def MockGetFileContents(filePath):
    if 'status' in filePath:
        return StatusFileSample
    elif 'heartbeat' in filePath:
        return HeartbeatSample
    elif 'HandlerState' in filePath:
        return 'Enabled'
    else:
        raise Exception("Don't know how to mock it")

class TestProtocolV1(unittest.TestCase):

    def _setUp(self):
       logger.AddLoggerAppender(logger.AppenderConfig({
           "type":"CONSOLE",
           "level":"VERBOSE",
           "console_path":"/dev/stdout"
       }))

    @Mockup(v1.restutil, 'HttpGet', MockHttpGet)
    def test_v1(self):
        os.chdir(CurrOS.GetLibDir())
        p = v1.ProtocolV1("foobar")
        p.refreshCache()
        p = v1.ProtocolV1("foobar")
        vmInfo = p.getVmInfo()
        self.assertNotEquals(None, vmInfo)
        self.assertNotEquals(None, vmInfo.getVmName())
        certs = p.getCerts()
        self.assertNotEquals(None, certs)
        extensions = p.getExtensions()
        self.assertNotEquals(None, extensions)
        ext = extensions[0]
        self.assertEquals('1.1', ext.getTargetVersion('1.4')['version'])
   
    @Mockup(v1.restutil, 'HttpPost', MockHttpPost)
    def test_report_provision_status(self):
        p = v1.ProtocolV1("foobar")
        p.goalState = v1.GoalState(GoalStateSample)
        p.reportProvisionStatus('Running', 'Provisioning', 'Everything is fine')
        self.assertEquals('http://foobar/machine?comp=health', 
                          MockHttpPost.args[0])
        self.assertTrue('Running' in MockHttpPost.args[1])
        self.assertTrue('Provisioning' in MockHttpPost.args[1])
        self.assertTrue('Everything is fine' in MockHttpPost.args[1])

    @Mockup(v1.restutil, 'HttpPut', MockHttpPut)
    @Mockup(v1.fileutil, 'GetFileContents', MockGetFileContents)
    @Mockup(v1.ProtocolV1, 'isResponsive', MockIsResponsive)
    @Mockup(os.path, 'isfile', MockIsFile)
    def test_report_agent_status(self):
        p = v1.ProtocolV1("foobar")
        p.extensions = v1.ExtensionsConfig(ExtensionsConfigSample)
        p.reportAgentStatus('1.0', 'Ready', 'Agent is running')
        self.assertEquals(('https://yuezhatest.blob.core.windows.net/vhds/'
                           'test-cs12.test-cs12.test-cs12.status?sr=b&sp=rw&'
                           'se=9999-01-01&sk=key1&sv=2014-02-14&sig=hfRh7gzUE'
                           '7sUtYwke78IOlZOrTRCYvkec4hGZ9zZzXo%3D'), 
                           MockHttpPut.args[0])
        self.assertTrue('Agent is running' in MockHttpPut.args[1])

if __name__ == '__main__':
    unittest.main()
