from app import customer_portal, user_organizations, chat

sample_get_header = {
    "version": "2.0",
    "routeKey": "$default",
    "rawPath": "/",
    "rawQueryString": "",
    "headers": {
        "sec-fetch-mode": "navigate",
        "x-amzn-tls-version": "TLSv1.2",
        "sec-fetch-site": "none",
        "accept-language": "en-US,en;q=0.9",
        "x-forwarded-proto": "https",
        "x-forwarded-port": "443",
        "x-forwarded-for": "76.146.33.162",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "x-amzn-tls-cipher-suite": "ECDHE-RSA-AES128-GCM-SHA256",
        "x-amzn-trace-id": "Root=1-655282b5-0f02bfc579085ee77bcb0e52",
        "host": "hry4lqp3ktulatehaowyzhkbja0mkjob.lambda-url.us-west-2.on.aws",
        "accept-encoding": "gzip, deflate, br",
        "sec-fetch-dest": "document",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    },
    "requestContext": {
        "accountId": "anonymous",
        "apiId": "hry4lqp3ktulatehaowyzhkbja0mkjob",
        "domainName": "hry4lqp3ktulatehaowyzhkbja0mkjob.lambda-url.us-west-2.on.aws",
        "domainPrefix": "hry4lqp3ktulatehaowyzhkbja0mkjob",
        "http": {
            "method": "GET",
            "path": "/",
            "protocol": "HTTP/1.1",
            "sourceIp": "76.146.33.162",
            "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        },
        "requestId": "30d49873-7aa1-4608-bf78-12620267a61d",
        "routeKey": "$default",
        "stage": "$default",
        "time": "13/Nov/2023:20:10:29 +0000",
        "timeEpoch": 1699906229342
    },
    "isBase64Encoded": False
}

sample_options_header = {
    "version": "2.0",
    "routeKey": "$default",
    "rawPath": "/",
    "rawQueryString": "",
    "headers": {
        "sec-fetch-mode": "cors",
        "referer": "http://hosted-sara.s3-website-us-west-2.amazonaws.com/",
        "x-amzn-tls-version": "TLSv1.2",
        "sec-fetch-site": "cross-site",
        "accept-language": "en-US,en;q=0.9",
        "x-forwarded-proto": "https",
        "origin": "http://hosted-sara.s3-website-us-west-2.amazonaws.com",
        "x-forwarded-port": "443",
        "x-forwarded-for": "76.146.33.162",
        "access-control-request-method": "POST",
        "accept": "*/*",
        "x-amzn-tls-cipher-suite": "ECDHE-RSA-AES128-GCM-SHA256",
        "x-amzn-trace-id": "Root=1-6552cde4-1c1e0aed08e79851166cc3b8",
        "access-control-request-headers": "content-type",
        "host": "hry4lqp3ktulatehaowyzhkbja0mkjob.lambda-url.us-west-2.on.aws",
        "accept-encoding": "gzip, deflate, br",
        "sec-fetch-dest": "empty",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    },
    "requestContext": {
        "accountId": "anonymous",
        "apiId": "hry4lqp3ktulatehaowyzhkbja0mkjob",
        "domainName": "hry4lqp3ktulatehaowyzhkbja0mkjob.lambda-url.us-west-2.on.aws",
        "domainPrefix": "hry4lqp3ktulatehaowyzhkbja0mkjob",
        "http": {
            "method": "OPTIONS",
            "path": "/",
            "protocol": "HTTP/1.1",
            "sourceIp": "76.146.33.162",
            "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        },
        "requestId": "c178d540-4f22-4571-bec6-a78320a2b2e6",
        "routeKey": "$default",
        "stage": "$default",
        "time": "14/Nov/2023:01:31:16 +0000",
        "timeEpoch": 1699925476393
    },
    "isBase64Encoded": False
}


class MockContext:
    def __init__(self, function_name):
        self.function_name = function_name


# test the customer portal with an invalid session
def test_request_headers_unauthorized_user():

    response = customer_portal(sample_get_header, MockContext('customer_portal'))

    assert response['statusCode'] == 401
    assert response['headers']['Content-Type'] == 'text/html'


# test the user orgs with an invalid session
def test_request_headers_unauthorized_orgs():

    response = user_organizations(sample_get_header, MockContext('user_organizations'))

    assert response['statusCode'] == 401
    assert response['headers']['Content-Type'] == 'text/html'


# test the chat with an invalid session
def test_request_headers_unauthorized_chat():

    response = chat(sample_get_header, MockContext('chat'))

    assert response['statusCode'] == 401
    assert response['headers']['Content-Type'] == 'text/html'


# test options
def test_request_headers_options_cors():

    response = customer_portal(sample_options_header, MockContext('customer_portal'))

    assert response['statusCode'] == 200
    assert response['headers']['Content-Type'] == 'application/json'
    assert response['headers']['Access-Control-Allow-Origin'] == sample_options_header['headers']['origin']
