import sys, os
import subprocess
from http.server import BaseHTTPRequestHandler,HTTPServer


class ServerException(Exception):
    '''服务器内部错误'''
    pass


class BaseCase(object):
    # 条件处理基类

    def handle_file(self, handler, full_path):
        try:
            with open(full_path, 'rb') as reader:
                content = reader.read()
            handler.send_content(content)
        except IOError as msg:
            msg = "'{0}' cannot be read: {1}".format(full_path, msg)
            handler.handle_error(msg)

    def index_path(self, handler):
        return os.path.join(handler.full_path, 'index.html')

    # 要求子类必须实现该借口
    def test(self, handler):
        assert False, 'Not implemented.'

    def act(self, handler):
        assert False, 'Not implemented.'


class CaseNoFile(BaseCase):
    '''该路径不存在'''

    def test(self, handler):
        return not os.path.exists(handler.full_path)

    def act(self, handler):
        raise ServerException("'{0}' not found".format(handler.path))


class CaseCgiFile(BaseCase):
    '''脚本文件处理'''

    def run_cgi(self, handler):
        data = subprocess.check_output(["python3", handler.full_path], shell=False)
        handler.send_content(data)

    def test(self, handler):
        return os.path.isfile(handler.full_path) and \
               handler.full_path.endswith('.py')

    def act(self, handler):
        self.run_cgi(handler)


class CaseExistingFile(BaseCase):
    '''该路径是文件'''

    def test(self, handler):
        return os.path.isfile(handler.full_path)

    def act(self, handler):
        self.handle_file(handler, handler.full_path)


class CaseDirectoryIndexFile(BaseCase):

    # 判断目标路径是否是目录&&目录下是否有index.html
    def test(self, handler):
        return os.path.isdir(handler.full_path) and \
               os.path.isfile(self.index_path(handler))

    # 响应index.html的内容
    def act(self, handler):
        self.handle_file(handler, self.index_path(handler))


class CaseAlwaysFail(BaseCase):
    '''所有情况都不符合时的默认处理类'''

    def test(self, handler):
        return True

    def act(self, handler):
        raise ServerException("Unknown object '{0}'".format(handler.path))


class RequestHandler(BaseHTTPRequestHandler):
    '''
    请求路径合法则返回相应处理
    否则返回错误页面
    '''


    '''
    此处BUG奇怪，按标准格式写就有BUG：
    HTTP/1.0 404 Not Found
    Content-Length: 182
    Content-type: text/html
    Date: Mon, 23 Jul 2018 02:28:57 GMT
    Server: BaseHTTP/0.6 Python/3.6.5

        <html>
        <body>
        <h1>Error accessing /time.py</h1>
        <p>'RequestHandler' object has no attribute 'handle_file'</p>
        </body>
        </html>
    把网站的不标准写法的代码贴过来就正常，调调缩进改成标准写法也正常
    '''
    Cases = [CaseNoFile(),
             CaseCgiFile(),
             CaseExistingFile(),
             CaseDirectoryIndexFile(),
             CaseAlwaysFail()]


    # 错误页面模板
    Error_Page = """\
        <html>
        <body>
        <h1>Error accessing {path}</h1>
        <p>{msg}</p>
        </body>
        </html>
        """

    def do_GET(self):
        try:

            # 得到完整的请求路径
            self.full_path = os.getcwd() + self.path

            # 遍历所有的情况并处理
            for case in self.Cases:
                if case.test(self):
                    case.act(self)
                    break

        # 处理异常
        except Exception as msg:
            self.handle_error(msg)

    def handle_error(self, msg):
        content = self.Error_Page.format(path=self.path, msg=msg)
        self.send_content(content.encode("utf-8"), 404)

    # 发送数据到客户端
    def send_content(self, content, status=200):
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


if __name__ == '__main__':
    serverAddress = ('', 8080)
    server = HTTPServer(serverAddress, RequestHandler)
    server.serve_forever()
