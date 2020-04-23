// Import external dependencies
import 'jquery';
import 'bootstrap';
import 'ekko-lightbox/dist/ekko-lightbox.min.js';
import 'bootstrap-table';
import 'bootstrap-table/dist/locale/bootstrap-table-nl-NL.min.js';
import 'bootstrap-table/dist/extensions/sticky-header/bootstrap-table-sticky-header.min.js';
import 'bootstrap-table/dist/extensions/mobile/bootstrap-table-mobile.min.js';
import naturalSort from 'javascript-natural-sort';

var Poliscoops = window.Poliscoops || {
  countries: {
    raw: undefined,
    id2name: {},
    name2id: {}
  }
};
window.Poliscoops = Poliscoops;

Poliscoops.map_countries = function() {
  Poliscoops.countries.raw.forEach(function (c) {
    Poliscoops.countries.id2name[c['@id']] = c['name'];
    Poliscoops.countries.name2id[c['name']] = c['@id'];
  });
};

Poliscoops.get_countries = function() {
  $.get('/countries.json', function (data) {
    console.log('Got countries data!');
    Poliscoops.countries.raw = data;
    Poliscoops.map_countries();
  });
};

Poliscoops.init = function() {
  console.log('poliscoops inited correctly!');

  Poliscoops.get_countries();

  // country checkbox selection thingie
  $('input[type="checkbox"]').on('change', function() {
    var state = $('#' + $(this).attr('id')).is(':checked');
    if (state) {
      $('label[for="'+ $(this).attr('id')+'"] i').removeClass('fa-square-o').addClass('fa-check-square-o');
    } else {
      $('label[for="'+ $(this).attr('id')+'"] i').removeClass('fa-check-square-o').addClass('fa-square-o');
    }
  });

  $('.form-countries .form-check').keydown(function (e) {
    console.log('countrie checkbox thingie keydown!');
    console.dir(e);
    if (e.originalEvent.key == "x") {
      console.log('x pressed!');
      $(e.target.firstElementChild).click();
    }
  });

  // countries for the collect modal
  $('#modal-subscribe').on('show.bs.modal', function (e) {
    // do something...
    console.log('show subscribe modal!');

    $('#modal-subscribe-location-info ul li').each(function (idx, item) {
      console.log('setting country name for ' + item);
      $(item).text(Poliscoops.countries.id2name[$(item).attr('data-location')]);
    });
  });
};

$(function() {
  console.log('jQuery init');
  Poliscoops.init();
});
