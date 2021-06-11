/***************************
****************************
********** FORM  ***********
****************************
***************************/
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, Math.max(ms, 0)));
}

    var reveal = Date.now() + 5000;

$(function() {
  
  let field = $('#answer-entry')
  let button = $('#answer-button')
  
    let div_field = document.getElementById("answer-entry");
    let div_button = document.getElementById("answer-button");
    
    let puzzle = document.getElementById("puzzle-holder");
    let checkdiv = document.getElementById("checking-div");
    let checkinsidediv = document.getElementById("checking-insidediv");
    let feedback = document.getElementById("guess-feedback");
    let rightbar = document.getElementById("right-bar");
    
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
    reveal = Date.now() + 5000;
    e.preventDefault()
    if (!field.val()) {
      field.focus()
      return
    }
    
    
    
    puzzle.style.display= "none";
    rightbar.style.opacity= 0;
    checkdiv.style.display= "block";
    
    checkinsidediv.innerHTML = '<img src="/static/img/mbicon.png" alt="" class="fit-inside rotating" style="max-width:60%; max-height:50%">';

    div_field.disabled = true;
    div_button.disabled = true;
    
    
    

    var data = {
      answer: field.val(),
    }
     $.ajax({
      type: 'POST',
      url: '',
      data: $.param(data),
      contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
      success:  function(data) {
        field.val('')
        fieldKeyup()
        if (data.status == 'correct') {
        sleep(reveal-Date.now()).then(()=>{
             checkinsidediv.innerHTML = '<p style="font-size:300px; color:lime">✓</p> ';
                rightbar.style.opacity= 1;
          sleep(2000).then(()=>{
                puzzle.style.display= "block";
                checkdiv.style.display= "none";
                div_field.disabled = false;
                div_button.disabled = false;
                if (document.getElementById("last-to-finish"))
                {
                window.location.href = document.getElementById("hunt-link").href
                }
                else
                {
                window.location.href = window.location.href;
                }
                });
            });
        } else if(data.status == "eureka"){
        sleep(reveal-Date.now()).then(()=>{
          checkinsidediv.innerHTML = '<img src="/static/img/milestone.png" alt="" class="fit-inside"  style="max-width:60%; max-height:70%"> ';
                rightbar.style.opacity= 1;
          sleep(2000).then(()=>{
                puzzle.style.display= "block";
                checkdiv.style.display= "none";
                div_field.disabled = false;
                div_button.disabled = false;
                });
           });
        } else if(data.status == "wrong"){
          
        sleep(reveal-Date.now()).then(()=>{
        checkinsidediv.innerHTML = '<p style="font-size:300px; color:#cc0000">✗</p> ';
                    rightbar.style.opacity= 1;
              sleep(2000).then(()=>{
                    puzzle.style.display= "block";
                    checkdiv.style.display= "none";
                    div_field.disabled = false;
                    div_button.disabled = false;
                    });
            });
        } else {
                   checkinsidediv.innerHTML = '<p style="font-size:50px; color:#cc0000"> Something went wrong <br> Do you have a team? </p> '
          waitCheckSynchronize(data.guess, data.timeout_length, data.timeout_end, data.unlocks)
        }
      },
      error: function(xhr, status, error) {
        button.removeData('cooldown')
        if (xhr.responseJSON && xhr.responseJSON.error == 'too fast') {
          message('You have to wait a few seconds beween consecutive guesses.', '')
        } else if (xhr.responseJSON && xhr.responseJSON.error == 'already answered') {
          message('Your team has already correctly answered this puzzle!', '')
        } else {
          message('There was an error submitting the answer.', error)
        }
        puzzle.style.display= "block";
        checkdiv.style.display= "none";
        rightbar.style.opacity= 1;
        div_field.disabled = false;
        div_button.disabled = false;
      },
      dataType: 'json',
    })
  })
})


function waitCheckSynchronize(guess, timeout_length, timeout) {
  var milliseconds = Date.parse(timeout) - Date.now()
  var difference = timeout_length - milliseconds

  // There will be a small difference in when the server says we should re-enable the guessing and
  // when the client thinks we should due to latency. However, if the client and server clocks are
  // different it will be worse and could lead to a team getting disadvantaged or seeing tons of
  // errors. Hence in that case we use our own calculation and ignore latency.
  if (difference < 0 || Math.abs(difference) > 1000) {
    difference = timeout_length
  }
  doCooldown(difference)
}

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

function addGuess(user, guess, correct, guess_uid) {
  var guesses_table = $('#guesses');
  guesses_table.prepend('<li><span class="guess-user">(' + encode(user) + ')</span><span class="guess-value">' + encode(guess) + '</span></li>')
  guesses.push(guess_uid)
}

function receivedNewGuess(content) {
  if (!guesses.includes(content.guess_uid)) {
    addGuess(content.by, content.guess, content.correct, content.guess_uid)

/*
    if (content.correct) {
      var message = $('#correct-answer-message')
      var html = `"${content.guess} was correct! Taking you ${content.text}. <a class="puzzle-complete-redirect" href="${content.redirect}">go right now</a>`
      if (message.length) {
        // The server already replied so we already put up a temporary message; just update it
        message.html(html)
      } else {
        // That did not happen, so add the message
        var form = $('.form-inline')
        form.after(`<div id="correct-answer-message">${html}</div>`)
        form.remove()
      }
      setTimeout(function () {window.location.href = content.redirect}, 3000)
    }
*/
  }
}

function receivedOldGuess(content) {
  if (!guesses.includes(content.guess_uid)) {
    addGuess(content.by, content.guess, content.correct, content.guess_uid)
  }
}





/***************************
****************************
********* HINTS ************
****************************
***************************/
var hints = [];

function receivedNewHint(content) {
  if(!hints.includes(content.hint_uid)){
    hints[content.hint_uid] = {'time': content.time, 'time_human': content.time_human, 'hint': content.hint}
    updateHints()
  }
}

function updateHints() {
  let hints_list = $("#hints")
  hints_list.empty()
  var entries = Object.entries(hints)
  entries.sort(function (a, b) {
    if (a[1].time < b[1].time) return -1
    else if(a[1].time > b[1].time) return 1
    return 0
  })
  entries.forEach(entry => {
    hints_list.append('<li><span class="guess-user">(' + entry[1].time_human + ')</span><span class="guess-value">' + (entry[1].hint) + '</span></li>')
  })
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

function receivedNewEureka(content) {
  if(!eurekas.includes(content.hint_uid)){
    addEureka(content.eureka, content.eureka_uid, content.feedback)
  }
}



/***************************
****************************
******** WEBSOCKET *********
****************************
***************************/
function receivedError(content) {
  throw content.error
}

var lastUpdated;
function openEventSocket() {
  const socketHandlers = {
    'new_hint': receivedNewHint,
    'old_hint': receivedNewHint,
    'new_eureka': receivedNewEureka,
    'old_eureka': receivedNewEureka,
    'new_guess': receivedNewGuess,
    'old_guess': receivedOldGuess,
    'error': receivedError,
  }

  var ws_scheme = (window.location.protocol == 'https:' ? 'wss' : 'ws') + '://'
  var sock = new WebSocket(ws_scheme + window.location.host + '/ws' + window.location.pathname)
  sock.onmessage = function(e) {
    var data = JSON.parse(e.data)
    lastUpdated = Date.now()

    if (!(data.type in socketHandlers)) {
      throw `Invalid message type: ${data.type}, content: ${data.content}`
    } else {
      var handler = socketHandlers[data.type]
      handler(data.content)
    }
  }
  sock.onerror = function() {
    message('Websocket is broken. You will not receive new information without refreshing the page.')
  }
  sock.onopen = function() {
    if (lastUpdated != undefined) {
      sock.send(JSON.stringify({'type': 'guesses-plz', 'from': lastUpdated}))
      sock.send(JSON.stringify({'type': 'hints-plz', 'from': lastUpdated}))
      sock.send(JSON.stringify({'type': 'unlocks-plz'}))
    } else {
      sock.send(JSON.stringify({'type': 'guesses-plz', 'from': 'all'}))
      sock.send(JSON.stringify({'type': 'hints-plz', 'from': 'all'}))
      sock.send(JSON.stringify({'type': 'unlocks-plz', 'from': 'all'}))
    }
  }
}



$(function() {
  openEventSocket()
})




/*
jQuery(document).ready(function($) {
  function is_visible(){
    var stateKey, keys = {
      hidden: "visibilitychange",
      webkitHidden: "webkitvisibilitychange",
      mozHidden: "mozvisibilitychange",
      msHidden: "msvisibilitychange"
    };
    for (stateKey in keys) {
      if (stateKey in document) {
        return !document[stateKey];
      }
    }
    return true;
  }


  // get_posts is set to be called every 3 seconds.
  // Each time get_posts does not receive any data, the time till the next call
  // gets multiplied by 2.5 until a maximum of 120 seconds, reseting to 3 when
  // get_posts receives data.
  // TODO: reset to 3 seconds when the user sends an answer
  var ajax_delay = 3;
  var ajax_timeout;

  var get_posts = function() {
    if(is_visible()){
      $.ajax({
        type: 'get',
        url: puzzle_url,
        data: {last_date: last_date},
        success: function (response) {
          var response = JSON.parse(response);
          messages = response.guess_list;
          if(messages.length > 0){
            ajax_delay = 3;
            for (var i = 0; i < messages.length; i++) {
              receiveMessage(messages[i]);
            };
            last_date = response.last_date;
          }
          else {
            ajax_delay = ajax_delay * 2.5;
            if(ajax_delay > 120){
              ajax_delay = 120;
            }
          }
        },
        error: function (html) {
          console.log(html);
          ajax_delay = ajax_delay * 2.5;
          if(ajax_delay > 120){
            ajax_delay = 120;
          }
        }
      });
    }
    ajax_timeout = setTimeout(get_posts, ajax_delay*1000);
  }

  ajax_timeout = setTimeout(get_posts, ajax_delay*1000);


  $('#sub_form').on('submit', function(e) {
    e.preventDefault();
    $("#answer_help").remove();
    $(this).removeClass("has-error");
    $(this).removeClass("has-warning");

    // Check for invalid answers:
    var non_alphabetical = /[^a-zA-Z \-_]/;
    if(non_alphabetical.test($(this).find(":text").val())) {
      $(this).append("<span class=\"help-block\" id=\"answer_help\">" +
                     "Answers will only contain the letters A-Z.</span>");
      $(this).addClass("has-error");
      return;
    }
    var spacing = /[ \-_]/;
    if(spacing.test($(this).find(":text").val())) {
      $(this).append("<span class=\"help-block\" id=\"answer_help\">" +
                     "Spacing characters are automatically removed from responses.</span>");
      $(this).addClass("has-warning");
    }
    $.ajax({
      url : $(this).attr('action') || window.location.pathname,
      type: "POST",
      data: $(this).serialize(),
      error: function (jXHR, textStatus, errorThrown) {
        if(jXHR.status == 403){
          error = "Guess rejected due to exessive guessing."
          $("<tr><td colspan = 3><i>" + error +"</i></td></tr>").prependTo("#sub_table");
        } else {
          var response = JSON.parse(jXHR.responseText);
          if("answer" in response && "message" in response["answer"][0]) {
            console.log(response["answer"][0]["message"]);
          }
        }
      },
      success: function (response) {
        clearTimeout(ajax_timeout);
        ajax_delay = 3;
        ajax_timeout = setTimeout(get_posts, ajax_delay*1000);
        response = JSON.parse(response);
        receiveMessage(response.guess_list[0]);
      }
    });
    $('#id_answer').val('');
  });

  // receive a message though the websocket from the server
  function receiveMessage(guess) {
    guess = $(guess);
    pk = guess.data('id');
    if ($('tr[data-id=' + pk + ']').length == 0) {
      guess.prependTo("#sub_table");
    } else {
      $('tr[data-id=' + pk + ']').replaceWith(guess);
    }
    if(guess.data('correct') == "True") {
      $("#id_answer").prop("disabled", true);
      $('button[type="submit"]').addClass("disabled");
      $('button[type="submit"]').attr('disabled', 'disabled');
    }
  }
});
*/
