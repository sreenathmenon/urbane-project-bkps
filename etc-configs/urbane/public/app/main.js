/**
 *  public/app/main.js
**/

/* global $, alert */

// *** application entry point *** //
(function (global) {
  // * global application namespace * //
  global.app = {
    submit: function () {
      console.log($('#accept-agreement').val())
      if (!$('#accept-agreement').prop('checked')) {
        alert('You have to accept agreements!')
        return
      }

      // prepare complex values
      if ($('[name=last_name]').val() && $('[name=first_name]').val()) {
        $('[name=contact_person]').val($('[name=last_name]').val() + ', ' + $('[name=first_name]').val())
      }
      if (
        $('[name=contact_address_endpoint]').val() &&
        $('[name=contact_address_locality]').val() &&
        $('[name=contact_address_region]').val() &&
        $('[name=contact_address_zip_code]').val() &&
        $('[name=contact_address_country]').val()
      ) {
        $('[name=contact_address]').val([
          $('[name=contact_address_endpoint]').val(),
          $('[name=contact_address_locality]').val(),
          $('[name=contact_address_region]').val(),
          $('[name=contact_address_zip_code]').val(),
          $('[name=contact_address_country]').val()
        ].join(', '))
      }
      if ($('#use-different-billing-address').prop('checked')) {
        if (
          $('[name=billing_address_endpoint]').val() &&
          $('[name=billing_address_locality]').val() &&
          $('[name=billing_address_region]').val() &&
          $('[name=billing_address_zip_code]').val() &&
          $('[name=billing_address_country]').val()
        ) {
          $('[name=billing_address]').val([
            $('[name=billing_address_endpoint]').val(),
            $('[name=billing_address_locality]').val(),
            $('[name=billing_address_region]').val(),
            $('[name=billing_address_zip_code]').val(),
            $('[name=billing_address_country]').val()
          ].join(', '))
        }
        $('[name=billing_use_contact_address]').val(0)
      } else {
        $('[name=billing_use_contact_address]').val(1)
        $('[name=billing_address]').val($('[name=contact_address]').val())
      }
      if ($('[name=billing_cc_expire_month]').val() && $('[name=billing_cc_expire_year]').val()) {
        $('[name=billing_cc_expire]').val($('[name=billing_cc_expire_month]').val() + '/' + $('[name=billing_cc_expire_year]').val())
      }
      if ($('[name=contact_phone_code]').val() && $('[name=contact_phone_number]').val()) {
        $('[name=contact_phone]').val($('[name=contact_phone_code]').val() + ' ' + $('[name=contact_phone_number]').val())
      }

      console.log($('#signup-form').serialize())
      // *** perform signup request *** //
      $('html').addClass('active-request')
      $('.invalid').removeClass('invalid')
      $('.error-message').html('')
      $.ajax({
        type: 'POST',
        url: '/signup',
        data: $('#signup-form').serialize(),
        success: function (response) {
          // redirect to 'success' page
          document.location = '/success'
        },
        error: function (response) {
          $('html').removeClass('active-request')
          if (response.status === 400) {
            // display errors
            var errors = JSON.parse(response.responseText)
            for (var param in errors) {
              var field = $('[name=' + param + ']')
              field.parents('.form-field').addClass('invalid').children('.error-message').html(errors[param])
            }
          } else {
            // show API error message
            $('html').addClass('api-error')
          }
        }
      })
    }
  }

  // remove `no-js` flag
  $('html').removeClass('no-js')
  // $('[name=contact_address_country]').val('US').removeClass('empty')

  // *** *** *** //
}(window))
