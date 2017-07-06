import os, sys, urllib2, urllib, json, requests
from datetime import datetime
# yahoo api:
baseurl = "https://query.yahooapis.com/v1/public/yql?"
current_dir = os.path.dirname(os.path.realpath(sys.argv[0])) + "/"
current_wx_string_file = current_dir + "current_wx_string.txt"
settings_file = current_dir + "settings.json"
with open(settings_file, 'r') as f:
    settings = json.load(f)
f.close()
location = settings['location']
wx_report_channel = settings['wx_report_channel']
webhook = settings['webhook']
wx_api_request = """
    select
        location,
        wind,
        item.condition,
        item.forecast,
        item.link
    from
        weather.forecast
    where
        woeid in
            (select
                woeid
            from
                geo.places(1)
            where text=\"""" + location + "\")"

# dangerous wx condition codes:
dangerous_wx_codes = ['0', '1', '2']
# rainy wx condition codes:
rainy_wx_codes = ['3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '35', '37', '38', '39', '40', '47']

def get_api_response(api_request):
    yql_url = baseurl + urllib.urlencode({'q': api_request}) + "&format=json"
    api_response = urllib2.urlopen(yql_url).read()
    return json.loads(api_response)

def write_string_to_file(string_to_write):
    print_current_time()
    fh = open(current_wx_string_file, "w")
    fh.write(string_to_write.encode('utf8'))
    fh.close()
    print "Updated data in file."

def read_file(file_to_read_from):
    f = file(file_to_read_from, 'r')
    return f.read().decode('utf8')

def print_current_time():
    print datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f") + "  ",

def post_to_slack(post_text, att_color, att_title, att_text):
    post_data = '{ \
        "channel": "' + wx_report_channel + '", \
        "text": "' + post_text + '", \
        "attachments": [ \
            { \
                "color": "' + att_color + '", \
                "title": "' + att_title + '", \
                "text": "' + att_text + '", \
                "mrkdwn_in": ["text"] \
            } \
        ] \
    }'
    print_current_time()
    print "Requested to post to Slack channel. Result:",
    r = requests.post(webhook, data=post_data.encode('utf8'))
    print(r.status_code, r.reason)

print_current_time()
print "Checking weather and forecast."
# perform API request:
forecast_data = get_api_response(wx_api_request)
# process the response:
response_block = forecast_data['query']['results']['channel'][0]
response_forecast = response_block['item']['forecast']
current_location_to_display = response_block['location']['city'] + "," + response_block['location']['region']
response_item = response_block['item']
response_condition = response_item['condition']
response_wind = response_block['wind']
current_wx_code = response_condition['code']
forecast_code = response_forecast['code']
current_wx_text = response_condition['text']
forecast_text = response_forecast['text']
condition_displaying_string = ""
forecast_displaying_string = ""
forecast_low_temp = response_forecast['low']
forecast_high_temp = response_forecast['high']
wx_provider_link = response_item['link'].split("*")[1]
if int(forecast_low_temp) < 0: forecast_low_temp = "(" + forecast_low_temp + ")"
if int(forecast_high_temp) < 0: forecast_high_temp = "(" + forecast_high_temp + ")"
# code 3200 stands for "unavailable"
if current_wx_code <> '3200': condition_displaying_string = "*_" + current_wx_text.lower() + "_*, "
if forecast_code <> '3200': forecast_displaying_string = "*_" + forecast_text.lower() + "_*, "
if current_wx_code in dangerous_wx_codes or forecast_code in dangerous_wx_codes:
    dangerous_wx = True
else:
    dangerous_wx = False
if current_wx_code in rainy_wx_codes or forecast_code in rainy_wx_codes:
    rainy_wx = True
else:
    rainy_wx = False
current_wx_string_to_display = "*Weather*: " + condition_displaying_string + \
    "temperature " + response_condition['temp'] + u'\u00B0' + "F, " + "wind: from " + \
    response_wind['direction'] + \
    u'\u00B0' +" at " + response_wind['speed'] + " mph, reported on: " + response_condition['date'] + "."
forecast_string_to_display = "*Recent forecast* for " + current_location_to_display + ", for " + \
    response_forecast['day'] + ", " + response_forecast['date'] + ": " + forecast_displaying_string + \
    "temperatre " + forecast_low_temp + "-" + forecast_high_temp + u'\u00B0' + "F."

wx_string_to_display = forecast_string_to_display + "\n" + current_wx_string_to_display + "\n" + \
    "Data provided by: <" + wx_provider_link + "|Yahoo! Weather>"
# read the last report from file:
wx_string_in_file = read_file(current_wx_string_file)
# if we got more recent data:
if wx_string_in_file <> wx_string_to_display:
    write_string_to_file(wx_string_to_display)
    if dangerous_wx:
        post_to_slack("Attention <!channel>:", "danger", ":tornado: Dangerous weather conditions!", wx_string_to_display)
    elif rainy_wx:
        post_to_slack("", "warning", ":umbrella_with_rain_drops: Bring an umbrella!", wx_string_to_display)
    else:
        print_current_time()
        print "No rain or dangerous weather conditions reported."
else:
    print_current_time()
    print "No need to update data in file and on Slack."
print "---------------------------------------"
