var owa_cur_date = new Date();
var owa_cur_year = owa_cur_date.getFullYear();
var OpenWOBApp = window.OpenWOBApp || {
  "api_base_url": "http://api.openwob.nl/v0",
  "start_date": (owa_cur_year - 1) + "-01-01T00:00:00",
  "end_date": owa_cur_year + "21-31T23:59:59",
  "data":{
    "delay": 0,
    "months": [],
    "words": []
  }
};

OpenWOBApp.init = function() {
  // init here

  $('.vote-btn').click(function (e) {
    var wob_id = $(this).attr('data-vote-id');
    var vote_type = $(this).attr('data-vote-type');
    var vote_url = "/" + OpenWOBApp.gov_slug + "/verzoek/" + wob_id + "/vote/" + vote_type;

    $.ajax({
        url: vote_url,
        type: "GET",
        contentType: "application/json",
        success: function (data) {
          alert(data);
        }
    });

    return false;
  });
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
      "start_date": {},
      "significant_wordcloud_text": {}
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

          OpenWOBApp.data.words = data.facets.significant_wordcloud_text.buckets;
          $('#tagcloud').empty();
          $.each(OpenWOBApp.data.words, function (idx, word) {
            var query_url = $('#tagcloud').attr('data-base-search-url') + '?query=' + word.key;
            $('#tagcloud').append($('<a href="' + query_url +'" data-count="' + word.score + '">' + word.key + '</span>'));
          });
          var tc = document.getElementById('tagcloud');
          OpenWOBApp.tagcloud(tc,'a');
        }
      }
  });
};

// from http://geekthis.net/post/javascript-tag-cloud/
OpenWOBApp.tagcloud = function(dom,tag) {
	var highVal = 0;
	var lowVal = Number.MAX_VALUE;
	var elements = dom.getElementsByTagName(tag);
	var minFont = parseInt(dom.getAttribute('data-minfont'),10);
	var maxFont = parseInt(dom.getAttribute('data-maxfont'),10);
	var fontDif = 0;
	var sizeDif = 0;
	var size = 0;
	var i = 0;
	var data = 0;

	for(i = 0; i < elements.length; ++i) {
		data = parseInt(elements[i].getAttribute('data-count'),10);
		if(data > highVal) {
			highVal = data;
		}
		if(data < lowVal) {
			lowVal = data;
		}
	}

	fontDif = maxFont - minFont;
	sizeDif = highVal - lowVal;

	for(i = 0; i < elements.length; ++i) {
		data = parseInt(elements[i].getAttribute('data-count'),10);
		size = (fontDif * (data - lowVal) / sizeDif) + minFont;
		size = Math.round(size);
		elements[i].style.fontSize = size + "px";
	}
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
