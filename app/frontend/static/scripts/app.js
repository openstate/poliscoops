var Poliflw = window.Poliflw || {
  "api_base_url": "https://api.poliflw.nl/v0",
};

Poliflw.init = function() {
  // init here

  // $('.rrssb-buttons').rrssb({
  //    // required:
  //    title: document.title,
  //    url: window.location.href
  //  });

  // make the button disappear
  $('.toggle-hide-after[data-toggle="collapse"]').on('click', function() {
    console.log('toggle hide after±');
    $(this).hide();
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
      var lower = $('#form-location input[type="search"]').val();
      var upper = lower.charAt(0).toUpperCase() + lower.substr(1);
      window.location = window.location.origin + '/zoeken?location=' + encodeURIComponent(upper);
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
        onClickAfter (n, a, item, event) {
          console.log('item ' + item.display + ' was selected!');
          window.location = window.location.origin + '/zoeken?location=' + encodeURIComponent(item.display);
        }
    }
  });
};


$(document).ready(function () {
  Poliflw.init();
});
