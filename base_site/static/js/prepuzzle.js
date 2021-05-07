/***************************
****************************
********** FORM  ***********
****************************
***************************/
$(function() {
  let field = $('#answer-entry')
  let button = $('#answer-button')

  function fieldKeyup() {
    if (!field.val()) {
      button.data('empty-answer', true)
    } else {
      button.removeData('empty-answer')
    }

    evaluateButtonDisabledState(button)
  }
  field.on('input', fieldKeyup)

  $('#guess-form').submit(function(e) {
  
    message(field.val(), '', 'error' )
    e.preventDefault()
    if (!field.val()) {
      field.focus()
      return
    }
    
    
    if (field.val() == {{puzzle.answer}}){
      correct_answer()
    }
    
  })
})


function correct_answer() {
  var form = $('#guess-form');
  if (form.length) {
    // We got a direct response before the WebSocket notified us (possibly because the WebSocket is broken
    // in this case, we still want to tell the user that they got the right answer. If the WebSocket is
    // working, this will be updated when it replies.
    message("Correct!", '', 'success');
  }
}


/***************************
**** BUTTON ANIMATIONS *****
***************************/
function evaluateButtonDisabledState(button) {
  var onCooldown = button.data('cooldown')
  var emptyAnswer = button.data('empty-answer')
  if (onCooldown || emptyAnswer) {
    button.attr('disabled', true)
  } else {
    button.removeAttr('disabled')
  }
}

function doCooldown(milliseconds) {
  var btn = $('#answer-button')
  btn.data('cooldown', true)
  evaluateButtonDisabledState(btn)

  setTimeout(function () {
    btn.removeData('cooldown')
    evaluateButtonDisabledState(btn)
  }, milliseconds)
}



/******************
*******************
**** MESSAGES *****
*******************
******************/

function encode(message){
  return message.replace(/[\u00A0-\u9999<>\&]/g, function(i) {
   return '&#'+i.charCodeAt(0)+';';
 });
}


function message(message, error = '', type = "danger") {
  var error_msg = $('<div class="alert alert-dismissible alert-' + type + '">' + message + ' ' + error + '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>')
  error_msg.appendTo($('#guess-feedback')).delay(3000).fadeOut(800, function(){$(this).remove()})
}




/***************************
****************************
********* GUESSES **********
****************************
***************************/

var guesses = [];

function addGuess(guess, correct, guess_uid) {
  var guesses_table = $('#guesses');
  guesses_table.prepend('<li><span class="guess-value">' + encode(guess) + '</span></li>')
  guesses.push(guess_uid)
}




