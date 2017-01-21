var sdp = angular.module('sdpApp', []);

sdp.config(function($interpolateProvider) {
    $interpolateProvider.startSymbol('[[').endSymbol(']]');
});

sdp.constant("moment", moment);

sdp.controller('eventController', function($scope, $http) {
    $scope.showCustom = false;

    var oneDay = 24*60*60*1000; // hours*minutes*seconds*milliseconds
    var secondDate = new Date();
    var firstDate = new Date(secondDate.getFullYear(),01,01);
    $scope.ytd  = Math.round(Math.abs((firstDate.getTime() - secondDate.getTime())/(oneDay)))
    $scope.getEvents = function(daysAgo) {
        console.log(daysAgo)
        $scope.startDate = moment().subtract((1 + daysAgo), 'days').format("YYYY-MM-DD");
        console.log($scope.startDate)
        $http.get('/users/dashboard/status/events/' + $scope.startDate + '/' + $scope.today.format("YYYY-MM-DD"))
            .then(function(response) {
                $scope.events = response.data
            });
    }
    $scope.events = $scope.getEvents(7)
    if ($scope.events == null) {
        $scope.events = false;
    };
    console.log($scope.events)
});

sdp.controller('progressBar', function($scope, $http, $timeout) {
    $scope.taskSuccess = null
    $scope.taskProgress = null
    $scope.value = 0;

    $scope.watchedTasks = []
    $scope.pendingTasks = []
    $scope.Math = window.Math;

    var poll = function() {
        $timeout(function() {

            $http.get('/users/dashboard/status/task_check')
                .then(function(response) {
                    console.log(response.data)
                    console.log(response.data.length)
                    console.log($scope.watchedTasks)
                    $scope.watchedTasks = response.data
                });

            poll();
        }, 1000);
    };


    var check_status = function(task) {
        $timeout(function() {
            task_id = task[Object.keys(obj)[0]]
            $http.get('/users/dashboard/status/' + task_id)
                .then(function(response) {
                    console.log(response.data)
                    task.status = response.data
                });

            check_status(task);
        }, 1000);
    };

    $scope.watchedTasks.forEach(check_status);
    poll();

});

function containsObject(obj, list) {
    var i;
    for (i = 0; i < list.length; i++) {
        if (angular.equals(list[i], obj)) {
            return true;
        }
    }

    return false;
}
