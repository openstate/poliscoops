// Import external dependencies
import 'jquery';
import 'bootstrap';
import 'ekko-lightbox/dist/ekko-lightbox.min.js';
import 'bootstrap-table';
import 'bootstrap-table/dist/locale/bootstrap-table-nl-NL.min.js';
import 'bootstrap-table/dist/extensions/sticky-header/bootstrap-table-sticky-header.min.js';
import 'bootstrap-table/dist/extensions/mobile/bootstrap-table-mobile.min.js';
import naturalSort from 'javascript-natural-sort';

$(function() {
  console.log('poliscoops inited correctly!');

  $('input[type="checkbox"]').on('change', function() {
    var state = $('#' + $(this).attr('id')).is(':checked');
    if (state) {
      $('label[for="'+ $(this).attr('id')+'"] i').removeClass('fa-square-o').addClass('fa-check-square-o');
    } else {
      $('label[for="'+ $(this).attr('id')+'"] i').removeClass('fa-check-square-o').addClass('fa-square-o');
    }
  });
});
