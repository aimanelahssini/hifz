import Foundation
import UserNotifications

/// Daily 22:00 reminder to recite Al-Waqi'a.
enum Reminder {
    static let id = "hifz.evening"
    static let actionRecite = "RECITE_NOW"
    static let categoryId = "HIFZ_REMINDER"
    static let surah = 56

    static func requestPermission() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { ok, err in
            Log.action("reminder: permission ok=\(ok) err=\(String(describing: err))")
        }
    }

    static func registerCategory() {
        let recite = UNNotificationAction(identifier: actionRecite, title: "Recite now", options: [.foreground])
        let cat = UNNotificationCategory(identifier: categoryId, actions: [recite], intentIdentifiers: [])
        UNUserNotificationCenter.current().setNotificationCategories([cat])
    }

    static func isEnabled(completion: @escaping (Bool) -> Void) {
        UNUserNotificationCenter.current().getPendingNotificationRequests { reqs in
            let on = reqs.contains { $0.identifier == id }
            DispatchQueue.main.async { completion(on) }
        }
    }

    static func setEnabled(_ on: Bool) {
        if on {
            schedule()
        } else {
            cancel()
        }
    }

    static func schedule() {
        requestPermission()
        registerCategory()
        let content = UNMutableNotificationContent()
        let name = Quran.name(surah)
        content.title = "Time for \(name)"
        content.body = "Recite \(name) before you sleep."
        content.sound = .default
        content.categoryIdentifier = categoryId
        content.userInfo = ["surah": surah]

        var date = DateComponents()
        date.hour = 22
        date.minute = 0
        let trigger = UNCalendarNotificationTrigger(dateMatching: date, repeats: true)
        let req = UNNotificationRequest(identifier: id, content: content, trigger: trigger)
        UNUserNotificationCenter.current().add(req) { err in
            Log.action("reminder: schedule err=\(String(describing: err))")
        }
        Log.action("reminder: scheduled 22:00")
    }

    static func cancel() {
        UNUserNotificationCenter.current().removePendingNotificationRequests(withIdentifiers: [id])
        Log.action("reminder: cancelled")
    }
}
