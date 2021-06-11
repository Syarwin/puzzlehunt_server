/***************************
****************************
********** FORM  ***********
****************************
***************************/

const delay = ms => new Promise(res => setTimeout(res, ms));
var lock = false
/* Hey, what are you doing here? This is just a prepuzzle, don't try to decrypt the answers looking at the source code please :) */
async function check() {
    let field = $('#answer-entry')
    if (!/[a-z0-9]/i.test(field.val()))
    {
      return;
    }
    
    if(lock){
      return;}
      
    lock = true

    
    
    let div_field = document.getElementById("answer-entry");
    let div_button = document.getElementById("answer-button");
    let button = $('#answer-button')
    
    let puzzle = document.getElementById("puzzle-holder");
    let checkdiv = document.getElementById("checking-div");
    let checkinsidediv = document.getElementById("checking-insidediv");
    let feedback = document.getElementById("guess-feedback");
    
    div_field.disabled = true;
    div_button.disabled = true;
    
    puzzle.style.display= "none";
    checkdiv.style.display= "block";
    
    checkinsidediv.innerHTML = '<img src="/static/img/mbicon.png" alt="" class="fit-inside rotating" style="max-width:60%; max-height:50%">';
    
    await delay(4000);
    
    
    if (!field.val()) {
      button.data('empty-answer', true)
    } else {
      button.removeData('empty-answer')
    }
    const prepuzzle_values = JSON.parse(document.getElementById('prepuzzle_values').textContent);
    hash = await sha256("SuperRandomInitialSalt" + field.val().replaceAll(" ", "").toLowerCase())
    
    addGuess(field.val(), false, field.val());
    
    if ( hash == prepuzzle_values['answerHash']){
      checkinsidediv.innerHTML = '<p style="font-size:300px; color:lime"> ✓ </p> '
      if ( prepuzzle_values['responseEncoded'].length > 0)
      {
        feedback.innerHTML = ('<p>Congratulations for solving this puzzle! \n' + decode(field.val().replaceAll(" ", "").toLowerCase(), prepuzzle_values['responseEncoded']) + '</p>')
      }
      else
      {
        feedback.innerHTML = ('<p>Congratulations for solving this puzzle! The answer was indeed "' + field.val().replaceAll(" ", "").toLowerCase() + '"</p>')      
      }
    }
    else if(prepuzzle_values['eurekaHashes'].includes(hash))
    {
      addEureka(field.val().replaceAll(" ", "").toLowerCase(), field.val().replaceAll(" ", "").toLowerCase(), '');
      checkinsidediv.innerHTML = '<img src="/static/img/milestone.png" alt="" class="fit-inside" style="max-width:60%; max-height:70%"> '
    }
    else
    {    
      checkinsidediv.innerHTML = '<p style="font-size:300px; color:#cc0000"> ✗ </p> '
    }
    await delay(2000);   
    
    document.getElementById('answer-entry').value = ''
    
    puzzle.style.display= "block";
    checkdiv.style.display= "none";
    div_field.disabled = false;
    div_button.disabled = false;
    lock=false
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
  if (!eurekas.includes(eureka_uid)){
    guesses_table.prepend('<li><span class="guess-user">' + encode(feedback) + '</span><span class="guess-value">' + encode(eureka) + '</span></li>') 
    eurekas.push(eureka_uid)
  }
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
