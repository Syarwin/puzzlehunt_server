/***************************
****************************
********** FORM  ***********
****************************
***************************/



/* Hey, what are you doing here? This is just a prepuzzle, don't try to decrypt the answers looking at the source code please :) */
async function check() {
    let field = $('#answer-entry')
    let button = $('#answer-button')
    
    
    
    if (!field.val()) {
      button.data('empty-answer', true)
    } else {
      button.removeData('empty-answer')
    }
    const prepuzzle_values = JSON.parse(document.getElementById('prepuzzle_values').textContent);
    hash = await sha256("SuperRandomInitialSalt" + field.val().replaceAll(" ", "").toLowerCase())
    
    addGuess(field.val(), false, field.val());
    
    if ( hash == prepuzzle_values['answerHash']){
      correct_answer()
      if ( prepuzzle_values['responseEncoded'].length > 0)
      {
        message('Congratulations for solving this puzzle! \n' + decode(field.val().replaceAll(" ", "").toLowerCase(), prepuzzle_values['responseEncoded']), '', 'success')
      }
    }
    else if(prepuzzle_values['eurekaHashes'].includes(hash))
    {
      addEureka(field.val(), hash, '');
      message(field.val(), ' is a Milestone!', 'primary' );
    }
    else
    {    
      message(field.val(), ' is not the correct answer' );
    }
    document.getElementById('answer-entry').value = ''
}


function checkKey(e) {
    if (e.key === 'Enter' || e.keyCode === 13) {
        check()
    }
}




$(function() {
  let field = $('#answer-entry')
  let button = $('#answer-button')

  function fieldKeyup() {

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
    
    
    
  })
})


function correct_answer() {
    message("Correct!", '', 'success');
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
  error_msg.appendTo($('#guess-feedback')).delay(8000).fadeOut(800, function(){$(this).remove()})
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



/***************************
****************************
********* EUREKAS **********
****************************
***************************/
var eurekas = [];

function addEureka(eureka, eureka_uid, feedback) {
  var guesses_table = $('#eurekas');
  guesses_table.prepend('<li><span class="guess-user">' + encode(feedback) + '</span><span class="guess-value">' + encode(eureka) + '</span></li>') 
  eurekas.push(eureka_uid)
}


async function sha256(message) {
    // encode as UTF-8
    const msgBuffer = new TextEncoder().encode(message);                    

    // hash the message
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);

    // convert ArrayBuffer to Array
    const hashArray = Array.from(new Uint8Array(hashBuffer));

    // convert bytes to hex string                  
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    return hashHex;
}


// simple way to decode a prepuzzle response string
function decode(key, string){
    output = [string.length]
    for (var i = 0; i < string.length; i++) {
        decoded_c = (string.charCodeAt(i) - key.charCodeAt(i % key.length) % 256);
        output[i] = String.fromCharCode(decoded_c);
        }
    return output.join("")
  }
