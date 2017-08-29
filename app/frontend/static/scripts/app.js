var owa_cur_date = new Date();
var owa_cur_year = owa_cur_date.getFullYear();
var OpenWOBApp = window.OpenWOBApp || {
  "api_base_url": "http://api.openwob.nl/v0",
  "start_date": (owa_cur_year - 1) + "-01-01T00:00:00",
  "end_date": owa_cur_year + "21-31T23:59:59",
  "data":{
    "delay": 0,
    "months": []
  }
};

OpenWOBApp.init = function() {
  // init here
};

OpenWOBApp.init_month_graph = function() {
  nv.addGraph(function() {
    var chart = nv.models.discreteBarChart()
        .x(function(d) { return d.key_as_string.slice(0, 7); })    //Specify the data accessors.
        .y(function(d) { return d.doc_count; })
        .staggerLabels(true)    //Too many bars and not enough room? Try staggering labels.
        .tooltips(true)        //Don't show tooltips
        .showValues(false)       //...instead, show the bar value right on top of each bar.
        ;

    d3.select('#graph-monthly svg')
        .datum([
          {
            key: 'Wob verzoeken', values: OpenWOBApp.data.months}])
        .transition().duration(500).call(chart);

    nv.utils.windowResize(chart.update);

    return chart;
  });
};

OpenWOBApp.get_data = function(start_date, end_date) {
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
      "delay_avg": {},
      "start_date": {}
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
          // first delay
          OpenWOBApp.data.delay = data.facets.delay_avg.value;
          $('.delay-lead .count').text(Math.floor(OpenWOBApp.data.delay));

          OpenWOBApp.data.months = data.facets.start_date.buckets;
          OpenWOBApp.init_month_graph();
        }
      }
  });
};


OpenWOBApp.set_date_years = function(start_year, end_year) {
  OpenWOBApp.start_date =start_year + "-01-01T00:00:00";
  OpenWOBApp.end_date = end_year + "-12-31T23:59:59";
  OpenWOBApp.get_data(OpenWOBApp.start_date, OpenWOBApp.end_date);
};

$(document).ready(function () {
  console.log('Ready to produce graphs!');
  OpenWOBApp.init();
});
