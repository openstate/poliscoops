var Poliflw = window.Poliflw || {
  "api_base_url": "https://api.poliflw.nl/v0",
  "form_email_target": null
};

Poliflw.queryParams = function() {
  var pairs = window.location.search.substring(1).split("&"),
    obj = {},
    pair,
    i;

  for ( i in pairs ) {
    if ( pairs[i] === "" ) continue;

    pair = pairs[i].split("=");
    obj[ decodeURIComponent( pair[0].replace(/\+/gm,"%20") ) ] = decodeURIComponent( pair[1].replace(/\+/gm,"%20") );
  }

  return obj;
};

Poliflw.init = function() {
  // init here

  // $('.rrssb-buttons').rrssb({
  //    // required:
  //    title: document.title,
  //    url: window.location.href
  //  });

  $('#form-email-subscribe').on('shown.bs.modal', function (e) {
    if (typeof(e.relatedTarget) == "object") {
      Poliflw.form_email_target = e.relatedTarget;
      var possible_filters = ['location', 'parties', 'query', 'user-query'];
      possible_filters.forEach(function (i) {
          var rt_value = $(e.relatedTarget).attr('data-form-email-subscribe-' + i);
          if (rt_value) {
            $('#form-email-subscribe-filters-' + i + ' span').html(rt_value);
          } else {
            $('#form-email-subscribe-filters-' + i + ' span').html('-');            
          }
      });
    }
  });
  // make the button disappear
  $('.toggle-hide-after[data-toggle="collapse"]').on('click', function() {
    console.log('toggle hide after±');
    $(this).hide();
  });

  $('#form-email-subscribe form').on('submit', function (e) {
    if (typeof(Poliflw.form_email_target) !== "object") {
      Poliflw.form_email_target = null;
      $('#form-email-subscribe').modal('hide');
      $(".modal-backdrop.in").hide();
      e.preventDefault();
      return false;
    }

    console.log('form submitted!!');
    var qp = Poliflw.queryParams();
    var possible_filters = ['location', 'parties'];
    console.dir(qp);
    var $frm = $('#form-email-subscribe form');
    var uq = $(Poliflw.form_email_target).attr('data-form-email-subscribe-user-query');
    var frq = $frm[0].frequency.value;
    var sqs = {
      simple_query_string : {
        query: uq,
        fields: ['title', 'description', 'data.value'],
        default_operator: "and"
      }
    };
    var json = {
      application: 'poliflw',
      email: $frm[0].email.value,
      frequency: frq == '' ? null : frq,
      description: uq,
      query: {
        query: sqs
      }
    };

    var num_filters = 0;
    var active_filters = [];
    possible_filters.forEach(function (i) {
      var rt_value = $(Poliflw.form_email_target).attr('data-form-email-subscribe-' + i);
      console.log('rt value : ' + rt_value);
      if (typeof(rt_value) !== "undefined") {
        num_filters++;
        active_filters.push({
          "term": {"data.key": i}
        });
        active_filters.push({
          "term": {"data.value": rt_value.toLowerCase()}
        });
      }
    });

    if (num_filters > 0) {
      json.query = {
        query: {
          bool: {
            must: sqs,
            filter: active_filters
          }
        }
      };
    }
    console.log('Number of filters active: ' + num_filters);
    console.log(JSON.stringify(json));

    // FIXME: remove the next two lines before deploying
    // e.preventDefault();
    // return false;

    $.ajax({
        type: "POST",
        contentType: "application/json",
        url: "/_email_subscribe",
        data: JSON.stringify(json),

        success: function (data) {
            let response = JSON.parse(data);

            if (response.status == "error") {
              console.log('FOUT ' + response.error);
            } else {
              console.log("Binoas says:");
              console.dir(response);
            }
        },

        error: function (error) {
          console.log('FOUT ' + error);
        }
    });

    Poliflw.form_email_target = null;
    $('#form-email-subscribe').modal('hide');
    $(".modal-backdrop.in").hide();
    e.preventDefault();
    return false;
  });

  $('.collapse').collapse({toggle: false});

  $('.description-collapse').on('click', function(e) {
    e.preventDefault();
    $($(this).attr('href')).collapse('toggle');

    if ($(this).find('span').hasClass('glyphicon-menu-down')) {
      $(this).find('span').removeClass('glyphicon-menu-down').addClass('glyphicon-menu-up');
    } else {
      $(this).find('span').removeClass('glyphicon-menu-up').addClass('glyphicon-menu-down');
    }
    return false;
  });

  $('.sidebar-collapse').on('click', function () {
    if ($('#sidebar').hasClass('hidden-xs')) {
      $('#sidebar').removeClass('hidden-xs').addClass('visible-xs-block').addClass('sidebar-mobile');
    } else {
      $('#sidebar').addClass('hidden-xs').removeClass('visible-xs-block').removeClass('sidebar-mobile');
    }
  });

  var daterangepickerlocale = {
    "format": "DD-MM-YYYY",
    "separator": " - ",
    "applyLabel":  "Toepassen",
    "cancelLabel":  "Annuleren",
    "fromLabel":  "Van",
    "toLabel":  "Tot",
    "customRangeLabel":  "Aanpasbaar",
    "weekLabel": "W",
    "daysOfWeek":  ["zon","maa","din","woe","don","vri","zat"],
    "monthNames":  ["januari","februari","maart","april","mei","juni","juli","augustus","september","oktober","november","december"],
    "firstDay": 1
  };

  $('input[name="daterange"]').daterangepicker(
    {
      "alwaysShowCalendars": true,
      "timePicker": false,
      "timePicker24Hour": false,
      "timePickerIncrement": 15,
      "ranges": {
        "Vandaag": [moment().startOf('day'), moment()],
        "Gisteren": [moment().subtract(1, 'days').startOf('day'), moment().subtract(1, 'days').endOf('day')],
        "Laatste 7 dagen": [moment().subtract(6, 'days').startOf('day'), moment()],
        "Laatste 30 dagen": [moment().subtract(29, 'days').startOf('day'), moment()],
        "Deze maand": [moment().startOf('month'), moment().endOf('month')],
        "Vorige maand": [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
      },
      'locale': daterangepickerlocale,
      //"startDate": "03/15/2016",
      //"endDate": "03/21/2016",
      "minDate": "01/01/1980",
      "maxDate": moment()
    }, function(start, end, label) {
      console.log("New date range selected: " + start.format('x') + ' to ' + end.format('x') + ' (predefined range: ' + label + ')');
      console.log('?from=' + start.format() + '&end=' + end.format());
      var new_url = JSON.parse(JSON.stringify(document.location.href));
      new_url = new_url.replace(/(\?|\&)date_(from|to)\=\d+/g, '');
      if (new_url.indexOf('?') >= 0) {
        new_url = new_url + '&';
      } else {
        new_url = new_url + '?';
      }
      new_url = new_url + 'date_from=' + start.format('x') + '&date_to=' + end.format('x');
      console.log('take away params: ' + new_url);
      document.location = new_url;
      //return false;
      //document.location = document.location.origin + document.location.pathname + '?from=' + encodeURIComponent(start.format()) + '&to=' + encodeURIComponent(end.format());
    }
  );

  $('#form-location').on('submit', function (e) {
      e.preventDefault();
      var qry = $('#form-location input[type="search"]').val();
      console.log('should do zoeken for [' + qry +'] now!');
      window.location = window.location.origin + '/zoeken?query=' + encodeURIComponent(qry);
      return false;
  });

  $('.js-typeahead').typeahead({
    order: "asc",
    source: {
        groupName: {
            // Array of Objects / Strings
            data: Poliflw.data.facets.location.buckets.map(function (i) { return i.key; })
        }
    },
    callback: {
        onInit: function () { console.log('typeahead inited!'); },
        onSearch: function (n,q) { console.log('looking for ' + q); },
        onShowLayout: function(n, q) { console.log('show layout'); },
        onClickAfter: function(n, a, item, event) {
          console.log('item ' + item.display + ' was selected!');
          window.location = window.location.origin + '/zoeken?location=' + encodeURIComponent(item.display);
        }
    }
  });

};


$(document).ready(function () {
  Poliflw.init();
});
