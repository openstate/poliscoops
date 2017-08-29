var OpenWOBApp = window.OpenWOBApp || {
  "api_base_url": "http://api.openwob.nl/v0",
  "data":{
    "delay": "-"
  }
};

OpenWOBApp.init = function() {
  // init here
};

OpenWOBApp.get_average_delay_in_period = function(start_date, end_date) {
  var req = {
    "filters": {
      "end_date": {
        "from": start_date,
        "to": end_date
      },
      "start_date":{
        "from": start_date,
        "to": end_date
      }
    },
    "facets": {
      "delay_avg": {}
    },
    "size": 0
  };

  $.ajax({
      url: OpenWOBApp.api_base_url + "/search",
      type: "POST",
      dataType: "json",
      data: JSON.stringify(req),
      contentType: "application/json",
      success: function (data) {
        console.log('Got average delay data');
        console.dir(data);

        if (typeof(data.facets.delay_avg.value) !== 'undefined') {
          OpenWOBApp.data.delay = data.facets.delay_avg.value;
          // TODO: update view
          $('.delay-lead .count').text(Math.floor(OpenWOBApp.data.delay));
        }
      }
  });
};

$(document).ready(function () {
  console.log('Ready to produce graphs!');
});
