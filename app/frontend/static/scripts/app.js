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
  // $('.toggle-hide-after[data-toggle="collapse"]').on('click', function() {
  //   console.log('toggle hide after±');
  //   $(this).hide();
  // });

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
};


$(document).ready(function () {
  Poliflw.init();
});
