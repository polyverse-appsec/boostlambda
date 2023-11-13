from app import customer_portal

sample_header = {
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


class MockContext:
    def __init__(self, function_name):
        self.function_name = function_name


# test the customer portal with an invalid session
def test_request_headers_unauthorized():

    response = customer_portal(sample_header, MockContext('customer_portal'))

    assert response['statusCode'] == 401
    assert response['headers']['Content-Type'] == 'text/html'
