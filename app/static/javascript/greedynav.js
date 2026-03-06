(function(){
  
    var GreedyNav = {
      collapseBreakpoint: 768,
      buttonWidth: 80,
      
      countLinks: function(items, navWidth) {
        items.removeClass("d-none");
        var width = 0;
        var i = 0;
        for (i; i<items.length; i++) {
          width = width + items[i].offsetWidth;
          if (width >= navWidth - this.buttonWidth) {
            return i;
          }
        }
        return i;
      },
      
      hideItems: function (items, linkCount) {
        var i = linkCount;
        for (i; i < items.length; i++) {
          items[i].classList.add("d-none");
        }
      },
      
      setupButton: function(items, linkCount) {
        var container = items.parent();
        if (!container.next().hasClass("greedy-dropdown")) {
          container.after('<div class="dropdown greedy-dropdown"><button class="btn btn-dark dropdown-toggle" type="button" id="greedyDropdown" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">More</button><div class="dropdown-menu dropdown-menu-right bg-dark" aria-labelledby="greedyDropdown"></div></div>');
        }
        var greedy = $(".dropdown.greedy-dropdown");
        greedy.toggleClass("d-none", (linkCount >= items.length ));
        greedy.find(".dropdown-menu").empty();
        for (let i= linkCount; i < items.length; i++) {
          var link = $(items[i]).find("a");
          greedy.find(".dropdown-menu").append('<a class="dropdown-item text-light" href="'+ link.attr("href")+'">'+link.text() +'</a>');
        }
      },
      
      reset: function(nav) {
        var items = nav.find(".nav-item");
        items.removeClass("d-none");
        nav.find(".greedy-dropdown").addClass("d-none");
      },
     
      initGreedyNav: function(nav) {
        var width = nav.find(".container").width() - nav.find(".navbar-header").width();
        var items = nav.find(".nav-item");
        var linkCount = this.countLinks(items, width);
        this.hideItems(items, linkCount);
        this.setupButton(items, linkCount);
      },
      
      onReady: function(navbar) {
        this.initGreedyNav(navbar);
      }
    }
    var gn = Object.create(GreedyNav);
    
    $(document).ready(function () {
      gn.onReady($(".navbar"));
    });
    
    $(window).resize(function(){
      if ($(window).width() >= gn.collapseBreakpoint)
        {
          gn.onReady($(".navbar"));
        }
      else {
        gn.reset($(".navbar"))
      }
      });
    }());